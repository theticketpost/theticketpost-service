import theticketpost.settings
import theticketpost.newspaper
import theticketpost.printer.ble

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

version = '0.0.1'
ble_scan_timout = 10

# WEB SERVER METHODS
@app.route('/')
@app.route('/home')
def home():
    config = theticketpost.settings.get_json("config")
    ticket_px_width = 0
    if 'printer' in config and 'dpi' in config['printer'] and 'paper_width' in config['printer']:
        dpi = config['printer']['dpi']
        paper_width = config['printer']['paper_width']
        ticket_px_width = round(dpi * paper_width / 25.4)

    return render_template('home.html', title='TheTicketPost', version=version, paper_width=ticket_px_width)

@app.route('/newspaper')
def newspaper():
    config = theticketpost.settings.get_json("config")
    ticket_px_width = 0
    if 'printer' in config and 'dpi' in config['printer'] and 'paper_width' in config['printer']:
        dpi = config['printer']['dpi']
        paper_width = config['printer']['paper_width']
        ticket_px_width = round(dpi * paper_width / 25.4)

    return render_template('newspaper.html', title='TheTicketPost', paper_width=ticket_px_width)

@app.route('/apps')
def apps():
    return render_template('apps.html', title='TheTicketPost', version=version)


@app.route('/store')
def store():
    return render_template('store.html', title='TheTicketPost', version=version)


@app.route('/settings')
def settings():
    return render_template('settings.html', title='TheTicketPost', version=version)


@app.route('/about')
def about():
    return render_template('about.html', title='TheTicketPost', version=version)



# API REST METHODS
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
            return "200"

    return "500"


@app.route('/api/printer/scan')
async def scan_for_printers():
    data = await theticketpost.printer.ble.scan_for_devices(ble_scan_timout)
    return jsonify(data)


@app.route('/api/printer/<string:address>/print')
async def print_image(address):
    theticketpost.newspaper.to_img('last_newspaper.png')
    data = await theticketpost.printer.ble.send_data(address, "")
    return data


def main():
    app.run(host='0.0.0.0', port=8080)
