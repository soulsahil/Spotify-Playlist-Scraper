from flask import Flask, request, redirect, jsonify, render_template
from flask_cors import CORS
import requests
from pathlib import Path
import os
import yt_dlp as youtube_dl
import re
import random

app = Flask(__name__)
CORS(app)

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://spotify-playlist-scraper-soulsahils-projects.vercel.app/callback")
SCOPE = "user-read-private user-read-email playlist-read-private"

@app.route('/')
def index():
    return render_template('index.html')

# List of sample playlist URLs
PLAYLISTS = [
    "https://open.spotify.com/playlist/27odqHwU1ni8J9lbIQih1C",
    "https://open.spotify.com/playlist/0rAdSPycrFdaBXh9xSW3ap",
    "https://open.spotify.com/playlist/7FoQZC8v4kmNctGLneRJDR",
    "https://open.spotify.com/playlist/5lfuu0un8XjAtUdxwtqjm4",
    "https://open.spotify.com/playlist/0i2S0eEdftTrmLKueMWUKX"
    # Add more playlists as needed
]

@app.route('/random_playlist')
def random_playlist():
    random_playlist_url = random.choice(PLAYLISTS)
    # Assuming a default audio quality of 128 kbps for random playlists
    return download_playlist_from_url(random_playlist_url, "128")

def download_playlist_from_url(playlist_url, audio_quality):
    playlist_id = extract_playlist_id(playlist_url)
    if not playlist_id:
        return "Invalid playlist URL."

    return redirect_to_spotify_auth(playlist_id, audio_quality)

def extract_playlist_id(playlist_url):
    try:
        return playlist_url.split("playlist/")[1].split("?")[0]
    except IndexError:
        return None

def redirect_to_spotify_auth(playlist_id, audio_quality):
    auth_params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": f"{playlist_id},{audio_quality}"
    }
    auth_url = "https://accounts.spotify.com/authorize"
    auth_redirect_url = f"{auth_url}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    
    return redirect(auth_redirect_url)

@app.route('/download_playlist', methods=['POST'])
def download_playlist():
    playlist_url = request.form.get('playlistUrl')
    audio_quality = request.form.get('audioQuality')

    if not playlist_url:
        return "Playlist URL not provided."
    
    if not audio_quality:
        return "Audio quality not provided."
    
    playlist_id_match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
    if not playlist_id_match:
        return "Invalid Playlist URL."
    
    playlist_id = playlist_id_match.group(1)

    # Perform Spotify authentication
    auth_params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": f"{playlist_id},{audio_quality}"
    }
    auth_url = "https://accounts.spotify.com/authorize"
    auth_redirect_url = f"{auth_url}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    
    return redirect(auth_redirect_url)

@app.route('/callback')
def callback():
    authorization_code = request.args.get('code')
    state = request.args.get('state')

    if not authorization_code:
        return "Authorization code not found in callback request."
    
    if not state:
        return "State parameter missing."
    
    playlist_id, audio_quality = state.split(',')

    # Exchange authorization code for access token
    token_url = "https://accounts.spotify.com/api/token"
    token_params = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }
    token_response = requests.post(token_url, data=token_params)

    if token_response.status_code != 200:
        return f"Failed to obtain access token. Status code: {token_response.status_code}. Response: {token_response.text}"

    access_token = token_response.json().get("access_token")

    if not access_token:
        return f"Access token not received. Response: {token_response.json()}"

    # Fetch playlist tracks
    headers = {"Authorization": f"Bearer {access_token}"}
    playlist_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    response = requests.get(playlist_tracks_url, headers=headers)

    if response.status_code == 200:
        playlist_data = response.json()
        tracks = playlist_data.get("items", [])
        track_names = [track["track"]["name"] for track in tracks]

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors':[{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }],
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        }

        for track_name in track_names:
            search_query = f'ytsearch:{track_name} official audio'
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                try:
                    info_dict = ydl.extract_info(search_query, download=False)
                    video_url = info_dict['entries'][0]['webpage_url']
                    audio_data = BytesIO()
                    ydl.download([video_url])
                    ydl.downloaded_files = [audio_data]
                    return send_file(audio_data, as_attachment=True, download_name=f'{track_name}.mp3', mimetype='audio/mpeg')
                except Exception as e:
                    print(f"Failed to download {track_name}: {str(e)}")
        
        return render_template('success.html', download_dir=download_dir)

    else:
        return f"Failed to fetch tracks from the playlist. Error: {response.text}"
