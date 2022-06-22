
import theticketpost.newspaper
import theticketpost.logger
import theticketpost.printer.ble
import theticketpost.scheduler
import theticketpost.applications

from flask import Flask, Response, render_template, request, jsonify, redirect, url_for

from loguru import logger

import os
import nest_asyncio
nest_asyncio.apply()

app = Flask(__name__)

version = '0.0.1'
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
@app.route('/api/log/stream')
def log_stream():
    return Response(theticketpost.logger.stream(), mimetype="text/plain", content_type="text/event-stream")

@app.route('/api/log/clear')
def log_clear():
    theticketpost.logger.clear()
    return "200"

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
            if (file == 'config'):
                ttp_scheduler.set_schedule(json)
            if (app_id):
                list_of_apps = theticketpost.applications.list()
                if app_id in list_of_apps.keys():
                    list_of_apps[app_id].refresh()

            return "200"

    return "500"


@app.route('/api/printer/scan')
async def scan_for_printers():
    data, code, msg = await theticketpost.printer.ble.scan_for_devices(ble_scan_timout)
    if code == 200:
        return jsonify(data)

    return Response(msg, status=code, mimetype='text/plain')


@app.route('/api/printer/<string:address>/print')
async def print_newspaper(address):
    logger.info("Printing ticket on " + address)
    code, msg = theticketpost.newspaper.print(address, port)
    if code == 200:
        logger.info(msg)
    return Response(msg, status=code, mimetype='text/plain')


@app.route('/api/apps/installed')
async def installed_apps():
    list =  []
    apps = theticketpost.applications.list()
    for key, app in apps.items():
        list.append( app.get_description() )

    return jsonify(list)


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
    theticketpost.applications.init(app)

    # load webserver
    logger.info( "Starting webserver on port: " + str(port) )
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
