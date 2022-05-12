import theticketpost.settings

from flask import Flask, render_template, request

app = Flask(__name__)

version = '0.0.1'


@app.route('/')
@app.route('/index')
@app.route('/dashboard')
def dashboard():
    name = 'Motherfucker'
    return render_template('dashboard.html', title='TheTicketPost', version=version, username=name)


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
        config['test'] = request.form['test']
        theticketpost.settings.save_json( "config", config )

    return render_template('settings.html', title='TheTicketPost', version=version, config=config)


@app.route('/about')
def about():
    return render_template('about.html', title='TheTicketPost', version=version)


def main():
    app.run( host='0.0.0.0', port=8080 )
