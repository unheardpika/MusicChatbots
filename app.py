from flask import Flask, send_from_directory, request, jsonify, redirect, session
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)  # Needed for session

# Spotify Authentication Setup
sp_oauth = SpotifyOAuth(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
    scope='user-read-playback-state user-modify-playback-state'
)

HISTORY_FILE = 'history.json'  # Song history file

# Helper Functions
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# Routes
@app.route('/')
def chat_page():
    return send_from_directory('static', 'chat.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect('/')

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    message = data.get('message', '').strip()

    token_info = session.get('token_info', None)
    if not token_info:
        return jsonify({'reply': f'Please log in with Spotify first: {request.host_url}login'})

    sp = Spotify(auth=token_info['access_token'])

    # Song Search Logic
    if ' by ' in message.lower():
        song_part, artist_part = message.lower().split(' by ', 1)
        query = f'track:{song_part.strip()} artist:{artist_part.strip()}'
    else:
        query = message

    results = sp.search(q=query, type='track', limit=1)
    tracks = results.get('tracks', {}).get('items', [])

    if tracks:
        track = tracks[0]
        song_name = track['name']
        artist = track['artists'][0]['name']
        track_url = track['external_urls']['spotify']
        track_uri = track['uri']
        album_image = track['album']['images'][0]['url'] if track['album']['images'] else ''

        try:
            sp.start_playback(uris=[track_uri])
            reply = f"▶️ Now playing: '{song_name}' by {artist} on your Spotify device!"

            history = load_history()
            history.append({
                'song': song_name,
                'artist': artist,
                'url': track_url,
                'album_image': album_image
            })
            save_history(history)

        except Exception as e:
            reply = f"⚠️ Error starting playback: {str(e)}.\nMake sure Spotify is open and active on your device."
    else:
        reply = "❌ No song found. Try another name."

    return jsonify({'reply': reply})

@app.route('/history')
def get_history():
    history = load_history()
    return jsonify(history)

if __name__ == '__main__':
    app.run(debug=True, port=8000)








