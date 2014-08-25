"""`main` is the top level module for this application."""

# Import the stuffs!
from flask import Flask, render_template, request, session
from flask import make_response, send_from_directory
from flask.ext.assets import Environment, Bundle
from flask.ext.sqlalchemy import SQLAlchemy
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic
import logging
import logging.config
import datetime
import os


from config import CONFIG, SECRET_KEY

app = Flask(__name__)
app.config.from_object('config')
assets = Environment(app)
db = SQLAlchemy(app)

from app.models import Player


###############################################################################
# Set up Logging

logdir = 'log'
if not os.path.exists(logdir):
    os.makedirs(logdir)

from logging.handlers import TimedRotatingFileHandler
file_handler = TimedRotatingFileHandler(logdir+'/server.log',
                                        'midnight', 1, 30)
formatline = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
file_handler.setFormatter(logging.Formatter(formatline))

app.logger.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)


#########################################################################
# Using JS and CSS bundlers to minify code.

# NOTE that these js files have to be loaded in a specific order.
js = Bundle(
    'js/vendor/*.js',
    'js/jquery/*.js',
    'js/foundation.min.js',
    'js/custom.js',
    filters='jsmin',
    output='gen/packed.js'
)
assets.register('js_all', js)

jsmine = Bundle(
    'js/minigame/mine.js',
    filters='jsmin',
    output='gen/minepacked.js'
)
assets.register('js_mine', jsmine)

css = Bundle('css/*.css',
             filters='yui_css', output='gen/packed.css')
assets.register('css_all', css)

#########################################################################


authomatic = Authomatic(CONFIG, SECRET_KEY)


@app.route('/login/<provider>/', methods=['GET', 'POST'])
def login(provider):
    response = make_response()
    result = authomatic.login(WerkzeugAdapter(request, response), provider)
    if result:
        app.logger.debug('auth result returned')
        if result.user:
            app.logger.debug('valid user returned')
            # ensure that the user is up to date....
            result.user.update()
            if (result.user.name and result.user.id):
                app.logger.debug('%s has logged in.' % result.user.name)
                user = Player.query.filter_by(oauth_id=result.user.id)
                if user.first():
                    print "player found"
                    user = user.first()
                else:
                    print "player not found"
                    user = Player(oauth_id=result.user.id,
                                  email=result.user.email,
                                  username=result.user.name)
                user.lastLogin = datetime.datetime.utcnow()
                db.session.add(user)
                db.session.commit()
                session['oauth_id'] = user.oauth_id

                return render_template('account.html', user=user)
            else:
                app.logger.error('user found, but no name/id found')
                # FIXME need better behavior here...
                return render_template('account.html')
        else:
            app.logger.error('result was empty')
            return render_template('account.html')
    # FIXME I don't like this bare response-
    # should be an error page if you get no result back.
    return response


@app.route('/logout')
def logout():
    session.clear()
    return render_template('index.html')


@app.route('/collect/<collectiontype>', methods=['GET', 'POST'])
def collect(collectiontype):
    """Place a request to collect data."""
    if session['oauth_id']:
        app.logger.debug('session oauth id:'+session['oauth_id'])
        player = Player.query.filter_by(oauth_id=session['oauth_id']).first()
        json = player.update_collection(collectiontype)
        app.logger.info(player.username+' is attempting to '+collectiontype)
        db.session.add(player)
        db.session.commit()
        return json
    else:
        return render_template('500.html')
    # if last_x +5 seconds is less than now()
    #   set new last_x
    #   calculate if anything is found
    #   return new last_x +5

#########################################################################


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images'),
                               'favicon.ico')


@app.route('/')
def indexpage():
    """This is the first page anyone sees."""
    return render_template('index.html')


@app.route('/mining')
def miningpage():
    """This is the first page anyone sees."""
    return render_template('minegame.html')


#########################################################################
# Error Handlers
@app.errorhandler(404)
def page_not_found(error):
    """Return a custom 404 error."""
    return render_template("404.html", request=request, e=error), 404


@app.errorhandler(500)
def page_borked(error):
    """Return a custom 500 error. Only hit when debugging is off."""
    db.session.rollback()
    return render_template("500.html", request=request, e=error), 500


if __name__ == '__main__':
    app.debug = False
    app.run(debug=False, port=8000)
