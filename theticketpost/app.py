
import theticketpost.newspaper
import theticketpost.logger
import theticketpost.printer.ble
import theticketpost.scheduler

from flask import Flask, Response, render_template, request, jsonify

from loguru import logger

import os
import nest_asyncio
nest_asyncio.apply()

app = Flask(__name__)

version = '0.0.1'
ble_scan_timout = 10
port = 8080

# WEB SERVER METHODS
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', title='TheTicketPost', version=version )

@app.route('/newspaper')
def newspaper():
    return render_template('newspaper.html', title='TheTicketPost')

@app.route('/apps')
def apps():
    return render_template('apps.html', title='TheTicketPost', version=version)


@app.route('/store')
def store():
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

    if (request.method == 'GET'):
        json = theticketpost.settings.get_json(file)
        return jsonify(json)

    if (request.method == 'POST'):
        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            json = request.json
            theticketpost.settings.save_json(file, json)
            ttp_scheduler.set_schedule(json)
            return "200"

    return "500"


@app.route('/api/printer/scan')
async def scan_for_printers():
    data = await theticketpost.printer.ble.scan_for_devices(ble_scan_timout)
    return jsonify(data)


@app.route('/api/printer/<string:address>/print')
async def print_newspaper(address):
    logger.info("Printing ticket on " + address)
    theticketpost.newspaper.print(address, port)
    logger.info("Print finished")
    return "200"


def main():
    global port
    config = theticketpost.settings.get_json("config")
    if 'webserver' in config and 'port' in config['webserver']:
        port = config['webserver']['port']
        
    global ttp_scheduler
    ttp_scheduler = theticketpost.scheduler.Scheduler(config)
    ttp_scheduler.start()

    logger.info( "Starting webserver on port: " + str(port) )
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
