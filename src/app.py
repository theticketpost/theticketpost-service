from flask import Flask, render_template

app = Flask(__name__)

version = '0.0.1'


@app.route('/')
@app.route('/index')
@app.route('/dashboard')
def dashboard():
    name = 'Motherfucker'
    version = '0.0.1'
    return render_template('dashboard.html', title='TheTicketPost', version=version, username=name)


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


def main():
    app.run( host='0.0.0.0', port=8080 )
