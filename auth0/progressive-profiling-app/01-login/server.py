"""Python Flask WebApp Auth0 integration example
"""
import json, urllib, urllib2
import cgi
from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from flask import request as r
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode
import requests

import constants

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

AUTH0_CALLBACK_URL = env.get(constants.AUTH0_CALLBACK_URL)
AUTH0_CLIENT_ID = env.get(constants.AUTH0_CLIENT_ID)
AUTH0_CLIENT_SECRET = env.get(constants.AUTH0_CLIENT_SECRET)
AUTH0_DOMAIN = env.get(constants.AUTH0_DOMAIN)
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = env.get(constants.AUTH0_AUDIENCE)
if AUTH0_AUDIENCE is '':
    AUTH0_AUDIENCE = AUTH0_BASE_URL + '/userinfo'

app = Flask(__name__, static_url_path='/public', static_folder='./public')
app.secret_key = constants.SECRET_KEY
app.debug = True


@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response


oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated


# Controllers API
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/callback')
def callback_handling():
    resp = auth0.authorize_access_token()
    token = resp

    url = AUTH0_BASE_URL + '/userinfo'
    headers = {'authorization': 'Bearer ' + resp['access_token']}
    resp = requests.get(url, headers=headers)
    userinfo = resp.json()

    session[constants.JWT_PAYLOAD] = userinfo

    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    # Configuration Values
    GRANT_TYPE = "client_credentials" # OAuth 2.0 flow to use
    
    # Get an Access Token from Auth0
    base_url = "https://{domain}".format(domain=AUTH0_DOMAIN)
    data = urllib.urlencode([('client_id', AUTH0_CLIENT_ID),
    		('client_secret', AUTH0_CLIENT_SECRET),
    		('audience', "https://tpmmexercise-app.auth0.com/api/v2/"),
    		('grant_type', GRANT_TYPE)])
    req = urllib2.Request(base_url + "/oauth/token", data)
    response = urllib2.urlopen(req)
    oauth = json.loads(response.read())
    access_token = oauth['access_token']
    req = urllib2.Request(base_url + "/api/v2/users/" + userinfo['sub'])
    req.add_header('Authorization', 'Bearer ' + access_token)
    req.add_header('Content-Type', 'application/json')

    response = urllib2.urlopen(req)
    res = json.loads(response.read())
    print res['logins_count']

    if res['logins_count'] % 2 == 0 :
	    return redirect('/profiling_1')

    return redirect('/dashboard')

@app.route('/profiling_1')
def profiling_1():
    return render_template('profiling_1.html', 
                           userinfo=session[constants.PROFILE_KEY],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))

@app.route('/profiling_1_handler', methods=['POST'])
def profiling_1_handler():
    
    car_color = r.form['carcolor']
    birth_city = r.form['birthcity']
    print car_color, birth_city

#    post_data = json.dumps({'usermetadata':{{'birth_city': birth_city}, { 'car_color':car_color}}})
#
#
#    # Configuration Values
#    GRANT_TYPE = "client_credentials" # OAuth 2.0 flow to use
#    
#    # Get an Access Token from Auth0
#    base_url = "https://{domain}".format(domain=AUTH0_DOMAIN)
#    data = urllib.urlencode([('client_id', AUTH0_CLIENT_ID),
#    		('client_secret', AUTH0_CLIENT_SECRET),
#    		('audience', "https://tpmmexercise-app.auth0.com/api/v2/"),
#    		('grant_type', GRANT_TYPE)])
#    req = urllib2.Request(base_url + "/oauth/token", data)
#    response = urllib2.urlopen(req)
#    oauth = json.loads(response.read())
#    access_token = oauth['access_token']
#    req = urllib2.Request(base_url + "/api/v2/users/" + userinfo['sub'])
#    req.add_header('Authorization', 'Bearer ' + access_token)
#    req.add_header('Content-Type', 'application/json')
#    
#    response = urllib2.Request(req, post_data)
#    res = urllib2.urlopen(response)
#    res = res.read()
#    print res
#
    return redirect('/dashboard')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session[constants.PROFILE_KEY],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=env.get('PORT', 3000))
