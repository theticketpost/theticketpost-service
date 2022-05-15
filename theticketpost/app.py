import theticketpost.settings

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

version = '0.0.1'

# WEB SERVER METHODS
@app.route('/')
@app.route('/index')
@app.route('/newspaper')
def newspaper():
    config = theticketpost.settings.get_json("config")
    ticket_px_width = 0
    if 'printer_dpi' in config and 'printer_paper_width' in config:
        dpi = config['printer_dpi']
        paper_width = config['printer_paper_width']
        ticket_px_width = round(dpi * paper_width / 25.4)

    return render_template('newspaper.html', title='TheTicketPost', version=version, paper_width=ticket_px_width)


@app.route('/apps')
def apps():
    return render_template('apps.html', title='TheTicketPost', version=version)


@app.route('/store')
def store():
    return render_template('store.html', title='TheTicketPost', version=version)


@app.route('/settings', methods=['POST', 'GET'])
def settings():
    config = theticketpost.settings.get_json("config")

    if ( request.method == 'POST' ):
        print( request.form )
        config['printer_dpi'] = int(request.form['printer_dpi'])
        config['printer_paper_width'] = int(request.form['printer_paper_width'])
        theticketpost.settings.save_json( "config", config )

    return render_template('settings.html', title='TheTicketPost', version=version, config=config)


@app.route('/about')
def about():
    return render_template('about.html', title='TheTicketPost', version=version)


# API REST METHODS
@app.route('/api/settings/<string:file>', methods=['GET', 'POST'])
def save_or_get_settings(file):

    if ( request.method == 'GET'):
        json = theticketpost.settings.get_json(file)
        return jsonify(json)

    if ( request.method == 'POST'):
        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            json = request.json
            theticketpost.settings.save_json(file, json)
            return "200"

    return "500"


def main():
    app.run( host='0.0.0.0', port=8080 )
