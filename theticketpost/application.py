from threading import Thread, Event
from loguru import logger
from flask import render_template, jsonify, url_for, request
from werkzeug.utils import secure_filename
import os
import json


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'svg', 'png'}


class Application(Thread):
    """Base class for theticketpost apps.

    Apps don't register anything on Flask. The core owns a fixed set of routes
    and dispatches to the app through `handlers()`, so apps can be installed,
    updated or removed while the server is running.
    """

    def __init__(self, name, file, desc, flaskApp):
        Thread.__init__(self, daemon=True)
        self.desc = desc
        # The module name may be internal (e.g. "ttp_app_text"); the app name is the one in desc.json
        self.name = desc.get("name", name)
        self.file = file
        self.root_path = os.path.dirname(os.path.realpath(file))
        self.template_folder = os.path.join(self.root_path, 'templates')
        self.static_folder = os.path.join(self.root_path, 'static')
        self.flaskApp = flaskApp
        self.stop_event = Event()


    def handlers(self):
        """API actions exposed under /api/apps/<name>/<action>: {action: (view, methods)}"""
        handlers = {'upload': (self.upload_file, ['POST'])}
        if self.desc.get("render_component"):
            handlers['component'] = (self.render_component, ['POST'])
        if self.desc.get("inspector"):
            handlers['inspector'] = (self.get_inspector_json, ['GET'])
        if self.desc.get("configuration"):
            handlers['configuration'] = (self.get_configuration_json, ['GET'])
        return handlers


    def static_url(self, filename):
        return url_for('app_static', name=self.name, filename=filename)


    def add_template_filter(self, func, name=None):
        """Register a Jinja filter. Use this instead of flaskApp.template_filter,
        which Flask rejects once the server has handled its first request."""
        self.flaskApp.jinja_env.filters[name or func.__name__] = func


    def run(self):
        self.stop_event.wait()
        logger.info(f"Application {self.name} stopped.")


    def stop(self):
        self.stop_event.set()


    def refresh(self):
        logger.debug("configuration file updated!")
        return


    def get_description(self):
        self.desc["icon_url"] = self.static_url('icon.svg') if self.has_icon() else None
        self.desc["needs_setup"] = self.needs_setup()
        return self.desc


    def has_icon(self):
        # The UI draws the icon with <use href="icon.svg#layer1">
        path = os.path.join(self.static_folder, 'icon.svg')
        try:
            with open(path) as icon:
                return 'id="layer1"' in icon.read()
        except OSError:
            return False


    def needs_setup(self):
        """True when a key/token setting or one marked "required" is still empty,
        or the AI provider the app uses isn't set up in Settings."""
        if not self.desc.get("configuration"):
            return False
        config = self.get_configuration_json().get_json() or []
        optional = {item.get("name") for item in self.desc.get("configuration_template", []) if item.get("optional")}
        for item in config:
            name = str(item.get("name", "")).lower()
            if item.get("name") in optional:
                continue
            if item.get("required") and not item.get("value"):
                return True
            if item.get("type") == "llm-provider":
                import theticketpost.llm
                if not theticketpost.llm.is_configured(item.get("value")):
                    return True
            elif ("key" in name or "token" in name) and not item.get("value"):
                return True
        return False


    def get_configuration(self):
        """The app settings: the current template with the values the user saved.
        Built from the template so settings added by an app update show up, and
        ones it removed go away."""
        template = self.desc.get("configuration_template", [])
        path_to_config = os.path.join(self.root_path, 'config.json')
        try:
            with open(path_to_config) as config_file:
                saved = json.load(config_file)
        except (OSError, ValueError):
            saved = []
        values = {item.get("name"): item.get("value") for item in saved if isinstance(item, dict)}
        config = []
        for item in template:
            item = dict(item)
            if item.get("name") in values:
                item["value"] = values[item["name"]]
            config.append(item)
        return config


    def get_configuration_value(self, name, default=None):
        value = next((item.get("value") for item in self.get_configuration() if item.get("name") == name), None)
        return default if value in (None, "") else value


    def get_configuration_json(self):
        return jsonify(self.get_configuration())


    def get_inspector_json(self):
        for attribute in self.desc["inspector_template"]:
            if attribute["type"] == "image":
                attribute["url"] = self.static_url('files/' + attribute["value"])
        return jsonify( { "refresh_component": self.desc["refresh_component"], "config": self.desc["inspector_template"] } )


    def render_component(self):
        logger.error("Overwrite this method in the specific module")
        return render_template('component.html')


    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


    def json_response(self, msg, code, url = ""):
        json = {}
        json["msg"] = msg
        json["code"] = code
        if ( url != "" ):
            json["url"] = url
        return jsonify(json)


    def upload_file(self):
        if 'file' not in request.files:
            msg = "No file part"
            logger.debug(msg)
            return self.json_response(msg, 400)

        file = request.files['file']

        if file.filename == '':
            msg = "No selected file"
            logger.debug(msg)
            return self.json_response(msg, 400)

        if file and self.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            files_folder = os.path.join(self.static_folder, 'files')
            os.makedirs(files_folder, exist_ok=True)
            file.save(os.path.join(files_folder, filename))
            msg = "Uploaded"
            logger.debug(msg)
            return self.json_response(msg, 200, self.static_url('files/' + filename))

        msg = "File type not allowed"
        logger.debug(msg)
        return self.json_response(msg, 400)
