
import theticketpost.newspaper
import theticketpost.logger
import theticketpost.printer.ble
import theticketpost.scheduler
import theticketpost.applications
import theticketpost.appstore
import theticketpost.llm
import theticketpost.backup
#import theticketpost.googleauth

from flask import Flask, Response, render_template, request, jsonify, redirect, url_for, send_from_directory, send_file, abort

from loguru import logger

import datetime
import io
import os
import sys
import threading

app = Flask(__name__)

version = '1.4.3'
ble_scan_timout = 10
port = 8080

# WEB SERVER METHODS
def check_minimal_config():
    config = theticketpost.settings.get_json("config")
    if ( len(config) == 0):
        logger.warning("Config file empty, redirecting user to settings")
        return redirect( url_for('settings') )


@app.route('/')
@app.route('/home')
def home():
    redirection = check_minimal_config()
    if redirection:
        return redirection
    return render_template('home.html', title='TheTicketPost', version=version)


@app.route('/newspaper')
def newspaper():
    return render_template('newspaper.html', title='TheTicketPost')


@app.route('/apps')
def apps():
    redirection = check_minimal_config()
    if redirection:
        return redirection
    return render_template('apps.html', title='TheTicketPost', version=version)


@app.route('/store')
def store():
    redirection = check_minimal_config()
    if redirection:
        return redirection
    return render_template('store.html', title='TheTicketPost', version=version)


@app.route('/settings')
def settings():
    return render_template('settings.html', title='TheTicketPost', version=version)


@app.route('/log')
def log():
    return render_template('log.html', title='TheTicketPost', version=version)


@app.route('/about')
def about():
    return render_template('about.html', title='TheTicketPost', version=version)



# API REST METHODS
def restart_process():
    logger.info("Restarting service...")
    # Werkzeug marks the server socket as inheritable: close it (and any other fd)
    # or the new process can't bind the port
    os.closerange(3, os.sysconf("SC_OPEN_MAX"))
    os.execv(sys.executable, [sys.executable] + sys.argv)


@app.route('/api/restart', methods=['POST'])
def restart_app():
    # Restart after the response has been sent
    threading.Timer(1.0, restart_process).start()
    return Response("Restarting", status=200, mimetype='text/plain')


@app.route('/api/log/stream')
def log_stream():
    return Response(theticketpost.logger.stream(), mimetype="text/plain", content_type="text/event-stream")


@app.route('/api/log/clear')
def log_clear():
    theticketpost.logger.clear()
    return "200"


def apply_config(config):
    """Puts a newly saved global config into effect."""
    ttp_scheduler.set_schedule(config)
    if config.get('repository', {}).get('name') != theticketpost.appstore.repository_name:
        theticketpost.appstore.init(app)


@app.route('/api/backup/export')
def backup_export():
    parts = request.args.get('parts', 'settings,newspaper').split(',')
    try:
        data = theticketpost.backup.export(parts, version)
    except theticketpost.backup.BackupError as e:
        return Response(str(e), status=400, mimetype='text/plain')
    name = 'theticketpost-' + '-'.join(p for p in theticketpost.backup.PARTS if p in parts) \
        + '-' + datetime.date.today().isoformat() + '.zip'
    return send_file(io.BytesIO(data), mimetype='application/zip', as_attachment=True, download_name=name)


@app.route('/api/backup/import', methods=['POST'])
def backup_import():
    upload = request.files.get('file')
    if not upload:
        return Response("No file", status=400, mimetype='text/plain')
    try:
        report = theticketpost.backup.import_backup(upload.read())
    except theticketpost.backup.BackupError as e:
        return Response(str(e), status=400, mimetype='text/plain')
    if report["settings"] is not None:
        apply_config(report["settings"])
    del report["settings"]
    return jsonify(report)


@app.route('/api/settings/<string:file>', methods=['GET', 'POST'])
def save_or_get_settings(file):

    app_id = ""
    folder = ""
    if ( "app" in request.args.keys() ):
        app_id = request.args.get("app")
        folder = "apps/" + app_id

    if (request.method == 'GET'):
        json = theticketpost.settings.get_json(file, folder=folder)
        return jsonify(json)

    if (request.method == 'POST'):
        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            json = request.json
            theticketpost.settings.save_json(file, json, folder=folder)
            if (file == 'config' and not app_id):
                apply_config(json)
            if (app_id):
                list_of_apps = theticketpost.applications.list()
                if app_id in list_of_apps.keys():
                    list_of_apps[app_id].refresh()

            return "200"

    return "500"


@app.route('/api/google-auth/get-token', methods=['POST'])
async def google_auth_get_token():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        logger.info(request.json)
        credential = request.json["credential"]
        scopes = request.json["scopes"]
        token = theticketpost.googleauth.get_token(credential, scopes)
        return jsonify({'access_token': token})

    return Response("patata", status=200, mimetype='text/plain')

#@app.route('/api/google-auth/oauth2callback')
#async def google_oauth_callback():


@app.route('/api/printer/scan')
async def scan_for_printers():
    data, code, msg = await theticketpost.printer.ble.scan_for_devices(ble_scan_timout)
    if code == 200:
        return jsonify(data)

    return Response(msg, status=code, mimetype='text/plain')


@app.route('/api/printer/<string:address>/print')
def print_newspaper(address):
    logger.info("Printing ticket on " + address)
    code, msg = theticketpost.newspaper.print(address, port)
    if code == 200:
        logger.info(msg)
    return Response(msg, status=code, mimetype='text/plain')


@app.route('/api/llm/providers')
def llm_providers():
    return jsonify(theticketpost.llm.providers())


@app.route('/api/apps/installed')
def installed_apps():
    list =  []
    apps = theticketpost.applications.list()
    for key, app in apps.items():
        list.append( app.get_description() )

    return jsonify(list)


@app.route('/api/apps/uninstall/<string:app_name>')
def uninstall_app(app_name):
    code, msg = theticketpost.applications.uninstall_application(app_name)
    return Response(msg, status=code, mimetype='text/plain') 


@app.route('/api/appstore/apps')
def store_apps():
    return jsonify( [obj for obj in theticketpost.appstore.list().values()] )


@app.route('/api/appstore/refresh', methods=['POST'])
def store_refresh():
    """Reads the store catalog again in the background (only when older than
    ?max_age seconds, if given). Poll /api/appstore/status to know when it's done."""
    max_age = request.args.get('max_age', default=0, type=int)
    theticketpost.appstore.refresh(max_age=max_age)
    return jsonify(theticketpost.appstore.status())


@app.route('/api/appstore/status')
def store_status():
    return jsonify(theticketpost.appstore.status())


@app.route('/api/updates')
def updates():
    """What the editor's update notice shows: a newer service version (or null)
    and the installed apps with a newer version in the store."""
    latest = theticketpost.appstore.core_version
    try:
        newer = bool(latest) and theticketpost.appstore.compare_version_number(latest, version) > 0
    except ValueError:  # not a valid version number
        newer = False
    return jsonify({
        "core": {"current": version, "latest": latest} if newer else None,
        "apps": [{"name": name, "version": entry["desc"]["version"]}
                 for name, entry in theticketpost.appstore.list().items() if entry["update"]],
    })


@app.route('/api/appstore/icon/<string:app_name>')
def store_app_icon(app_name):
    try:
        icon = theticketpost.appstore.get_icon(app_name)
    except Exception as e:
        logger.error(f"Could not download the icon of {app_name}: {e}")
        icon = None
    if icon is None:
        abort(404)
    return Response(icon, mimetype='image/svg+xml', headers={'Cache-Control': 'max-age=86400'})


@app.route('/api/appstore/install/<string:app_name>')
def install_app(app_name):
    code, msg, restart_required = theticketpost.appstore.install_application(app_name)
    return jsonify({'message': msg, 'restart_required': restart_required}), code


# Fixed routes shared by every app, so apps can be (un)installed while running
@app.route('/api/apps/<string:name>/<string:action>', methods=['GET', 'POST'])
def app_api(name, action):
    application = theticketpost.applications.get(name)
    if application is None:
        abort(404)

    handler = application.handlers().get(action)
    if handler is None:
        abort(404)

    view, methods = handler
    if request.method not in methods:
        abort(405)

    return view()


@app.route('/apps/<string:name>/static/<path:filename>')
def app_static(name, filename):
    application = theticketpost.applications.get(name)
    if application is None:
        abort(404)
    return send_from_directory(application.static_folder, filename)


# Old static URLs ('/<name>app_blueprint/static/...') saved in newspaper.json's rendered html
@app.route('/<string:legacy_prefix>/static/<path:filename>')
def legacy_app_static(legacy_prefix, filename):
    suffix = 'app_blueprint'
    if not legacy_prefix.endswith(suffix):
        abort(404)
    return app_static(legacy_prefix[:-len(suffix)], filename)


def main():
    global port
    config = theticketpost.settings.get_json("config")
    if 'webserver' in config and 'port' in config['webserver']:
        port = config['webserver']['port']

    # init scheduler
    global ttp_scheduler
    ttp_scheduler = theticketpost.scheduler.Scheduler(config)
    ttp_scheduler.start()

    # load applications
    theticketpost.llm.migrate_app_keys()
    theticketpost.applications.init(app)

    #load app store
    theticketpost.appstore.init(app)

    # load webserver
    logger.info( "Starting webserver on port: " + str(port) )
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
