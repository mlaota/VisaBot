import os

from flask import Flask
from threading import Thread

app = Flask('VisaBot')


@app.route('/')
def home():
    return "I'm alive"


def get_heroku_port(default=8080):
    return int(os.environ.get('PORT', default))


def run():
    app.run(host='0.0.0.0', port=get_heroku_port())


def keep_alive():
    t = Thread(target=run)
    t.start()
