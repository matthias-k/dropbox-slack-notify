# Adapted from https://github.com/dropbox/mdwebhook
from hashlib import sha256
import hmac
import json
import os
import threading
from urllib.parse import urlparse

from dropbox.client import DropboxClient, DropboxOAuth2Flow
from flask import abort, Flask, redirect, render_template, request, session, url_for
 
# App key and secret from the App console (dropbox.com/developers/apps)
#APP_KEY = os.environ['APP_KEY']
#APP_SECRET = os.environ['APP_SECRET']
 
app = Flask(__name__)
app.config.from_pyfile('default_config.py')
if os.path.isfile('app_config.py'):
    app.config.from_pyfile('app_config.py')
app.debug = True
 

def get_url(route):
    '''Generate a proper URL, forcing HTTPS if not running locally'''
    host = urlparse(request.url).hostname
    url = url_for(
        route,
        _external=True,
        _scheme='http' if host in ('127.0.0.1', 'localhost') else 'https'
    )

    return url

def get_flow():
    return DropboxOAuth2Flow(
        app.config['APP_KEY'],
        app.config['APP_SECRET'],
        get_url('oauth_callback'),
        session,
        'dropbox-csrf-token')

@app.route('/oauth_callback')
def oauth_callback():
    '''Callback function for when the user returns from OAuth.'''

    access_token, uid, extras = get_flow().finish(request.args)
 
    # Extract and store the access token for this user
    redis_client.hset('tokens', uid, access_token)

    process_user(uid)

    return redirect(url_for('done'))

cursors = {}
files = set()

def process_prefix(prefix, verbose=True):
    '''Call /delta for the given user ID and process any changes.'''
    global cursors
    global files

    # OAuth token for the user
    token = app.config['DROPBOX_APP_TOKEN']

    # /delta cursor for the user (None the first time)
    # cursor = redis_client.hget('cursors', uid)
    cursor = cursors.get(prefix)

    client = DropboxClient(token)
    has_more = True

    while has_more:
        result = client.delta(cursor, path_prefix=prefix)

        for path, metadata in result['entries']:
            if verbose:
                if metadata is None:
                    print("DELETED", path)
                    if path in files:
                        files.remove(path)
                elif path in files:
                    print('MODIFIED', path, metadata.get('modifier'))
                else:
                    print('ADDED', path, metadata.get('modifier'))
                    files.add(path)

        # Update cursor
        cursor = result['cursor']
        cursors[prefix] = cursor

        # Repeat only if there's more to do
        has_more = result['has_more']

def process_all(verbose=True):
    '''Call /delta for the given user ID and process any changes.'''
    print("CHANGES!")
    for prefix in app.config['DROPBOX_PATH_PREFIXES']:
        process_prefix(prefix, verbose=verbose)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect(get_flow().start())

@app.route('/done')
def done(): 
    return render_template('done.html')

def validate_request():
    '''Validate that the request is properly signed by Dropbox.
       (If not, this is a spoofed webhook.)'''

    signature = request.headers.get('X-Dropbox-Signature')
    return signature == hmac.new(app.config['DROPBOX_APP_SECRET'], request.data, sha256).hexdigest()

@app.route('/webhook', methods=['GET'])
def challenge():
    '''Respond to the webhook challenge (GET request) by echoing back the challenge parameter.'''

    return request.args.get('challenge')

@app.route('/webhook', methods=['POST'])
def webhook():
    '''Receive a list of changed user IDs from Dropbox and process each.'''
    print("INCOMING")

    # Make sure this is a valid request from Dropbox
    if not validate_request(): abort(403)

    #for uid in json.loads(request.data)['delta']['users']:
        # We need to respond quickly to the webhook request, so we do the
        # actual work in a separate thread. For more robustness, it's a
        # good idea to add the work to a reliable queue and process the queue
        # in a worker process.
    threading.Thread(target=process_all).start()
    return ''

if __name__=='__main__':
    process_all(verbose=False)
    app.run(debug=True, host='0.0.0.0', port=12345)
    #threading.Thread(target=process_user, args=(uid,)).start()
    
