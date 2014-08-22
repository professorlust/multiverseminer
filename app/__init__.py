"""`main` is the top level module for this application."""

# Import the stuffs!
from flask import Flask, render_template, request, g, session, flash, redirect, url_for, make_response,send_from_directory
from flask.ext.assets import Environment, Bundle
from flask.ext.sqlalchemy import SQLAlchemy
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic
import logging
import logging.config
import ConfigParser
import datetime
import json
import re
import os
import traceback


from config import CONFIG

app = Flask(__name__)
app.config.from_object('config')
assets = Environment(app)
db = SQLAlchemy(app)

from app import models


#########################################################################
# Set up Logging

logdir='log'
if not os.path.exists(logdir):
    os.makedirs(logdir)

from logging.handlers import TimedRotatingFileHandler
file_handler = TimedRotatingFileHandler( logdir+'/server.log', 'midnight', 1, 30)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))

app.logger.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)


#########################################################################
# Using JS and CSS bundlers to minify code.

js = Bundle(
#NOTE that these js files have to be loaded in a specific order.
'js/vendor/*.js',
'js/jquery/*.js',
'js/foundation.min.js',
'js/custom.js',
            filters='jsmin',
            output='gen/packed.js'
)
assets.register('js_all', js)

css = Bundle('css/*.css',
            filters='yui_css', output='gen/packed.css')
assets.register('css_all', css)

#########################################################################


authomatic = Authomatic(CONFIG, 'random secret string for session signing')

@app.route('/login/<provider_name>/', methods=['GET', 'POST'])
def login(provider_name):
    response = make_response()
    result = authomatic.login(WerkzeugAdapter(request, response), provider_name)
    if result:
        app.logger.debug('auth result returned')
        if result.user:
            app.logger.debug('valid user returned')
            # ensure that the user is up to date....
            result.user.update()
            if  (result.user.name and result.user.id):
                app.logger.debug('user ' + result.user.name + ' has logged in.')
                #TODO store user result data in the DB or session
                # Show that everything is ok.
                return render_template('account.html', result=result)
            else:
                # FIXME need better behavior here...
                return render_template('account.html', result=result)
        else:
            # FIXME No user was found...?
            return render_template('account.html', result=result)
    # FIXME I don't like this bare response- should be an error page if you get no result back.
    return response

#########################################################################

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def indexpage():
    """This is the first page anyone sees."""
    return render_template('index.html')


#########################################################################
# Error Handlers
@app.errorhandler(404)
def page_not_found(error):
    """Return a custom 404 error."""
    return render_template("404.html", request=request,e=error), 404

@app.errorhandler(500)
def page_borked(error):
    """Return a custom 500 error. Only hit when debugging is off."""
    db.session.rollback()
    return render_template("500.html", request=request, e=error), 500


if __name__ == '__main__':
    app.debug = False
    app.run(debug=False, port=8000)


