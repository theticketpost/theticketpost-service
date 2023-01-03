from threading import Thread
from loguru import logger
import time
from flask import Blueprint, render_template, jsonify, url_for, request, redirect
from werkzeug.utils import secure_filename
import os
import json


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'svg', 'png'}

class Application(Thread):
    def __init__(self, name, file, desc):
        Thread.__init__(self)
        self.desc = desc
        self.name = name
        self.file = file

        self.blueprint = Blueprint(self.name + 'app_blueprint', self.name,
            template_folder='templates',
            static_folder='static',
            static_url_path='/' + self.name + 'app_blueprint/static')

        if ( self.desc["render_component"] ):
            self.blueprint.add_url_rule('/api/apps/' + self.name + '/component',
                view_func=self.render_component,
                methods=['POST'])

        if ( self.desc["inspector"] ):
            self.blueprint.add_url_rule('/api/apps/' + self.name + '/inspector',
                view_func=self.get_inspector_json)

        if ( self.desc["configuration"] ):
            self.blueprint.add_url_rule('/api/apps/' + self.name + '/configuration',
                view_func=self.get_configuration_json)

        self.blueprint.add_url_rule('/api/apps/' + self.name + '/upload',
            view_func=self.upload_file,
            methods=['POST'])


    def run(self):
        while True:
            #logger.debug("ImageApp is waiting for you")
            time.sleep(30)



    def refresh(self):
        logger.debug("configuration file updated!")
        return



    def get_description(self):
        if ( self.desc["render_component"] ):
            self.desc["icon_url"] = url_for( self.name + 'app_blueprint.static', filename='icon.svg')
        return self.desc



    def get_configuration_json(self):
        path_to_config = os.path.join(os.path.dirname(self.file), 'config.json')
        if os.path.exists(path_to_config):
            with open(path_to_config) as config_file:
                data = json.load(config_file)
                return jsonify(data)

        return jsonify( self.desc["configuration_template"] )



    def get_inspector_json(self):
        for attribute in self.desc["inspector_template"]:
            if attribute["type"] == "image":
                attribute["url"] = url_for( self.name + 'app_blueprint.static', filename='files/' + attribute["value"])
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
            file.save(os.path.join(os.path.join(os.path.dirname(self.file), 'static/files'), filename))
            msg = "Uploaded"
            logger.debug(msg)
            return self.json_response(msg, 200, url_for(self.name + 'app_blueprint.static', filename='files/' + file.filename))
