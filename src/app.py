from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/index')
def hello():
    name = 'Motherfucker'
    return render_template('hello.html', title='TheTicketPost', username=name)

def main():
    app.run( host='0.0.0.0', port=8080 )
