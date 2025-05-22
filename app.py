import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

# --- Spotify API Configuration ---
# Prompt the user for Client ID and Client Secret
SPOTIPY_CLIENT_ID = input("Please paste your Spotify Client ID and press Enter: ").strip()
SPOTIPY_CLIENT_SECRET = input("Please paste your Spotify Client Secret and press Enter: ").strip()

if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    print("WARNING: Spotify Client ID or Client Secret was not provided.")
    print("Spotify API functionality will be limited or unavailable.")

sp = None
try:
    # Initialize Spotify client with Client Credentials Flow
    # This flow is suitable for public data access (like public playlists)
    # and does not require user authentication.
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    ))
    # Test credentials by trying to get a token
    sp.auth_manager.get_access_token(as_dict=False)
    print("Spotify API credentials successfully loaded.")
except Exception as e:
    print(f"Error initializing Spotipy or validating credentials: {e}")
    print("Spotify API functionality will be limited or unavailable. Please check your Client ID and Client Secret.")

# --- File to store album data ---
ALBUMS_FILE = 'albums.json'

def load_albums():
    """Loads existing album data from the JSON file."""
    if not os.path.exists(ALBUMS_FILE):
        return []
    try:
        with open(ALBUMS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {ALBUMS_FILE} is corrupted or empty. Starting with an empty list.")
        return []
    except Exception as e:
        print(f"Error loading albums from file: {e}")
        return []

def save_albums(albums):
    """Saves album data to the JSON file."""
    try:
        with open(ALBUMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(albums, f, indent=4)
    except Exception as e:
        print(f"Error saving albums to file: {e}")

@app.route('/process_playlist', methods=['POST'])
def process_playlist():
    """
    Processes a Spotify playlist URL, extracts album and artist information,
    and updates the stored list of albums.
    """
    data = request.get_json()
    playlist_url = data.get('playlist_url')

    if not playlist_url:
        return jsonify({'error': 'No playlist URL provided'}), 400

    if not sp:
        return jsonify({'error': 'Spotify API not initialized or invalid credentials. Restart the app and provide valid credentials.'}), 500

    try:
        # Extract playlist ID from URL
        # Example URL: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
        # ID is 37i9dQZF1DXcBWIGoYBM5M
        parts = playlist_url.split('/')
        playlist_id = None
        for i, part in enumerate(parts):
            if part == 'playlist' and i + 1 < len(parts):
                playlist_id = parts[i+1].split('?')[0] # Remove query parameters
                break

        if not playlist_id:
            return jsonify({'error': 'Invalid Spotify playlist URL. Could not extract ID.'}), 400

        print(f"Processing playlist ID: {playlist_id}")

        # Fetch playlist tracks
        results = sp.playlist_items(playlist_id)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        current_albums = load_albums()
        unique_albums = {(album['name'], album['artist']) for album in current_albums}

        new_albums_found = []
        for item in tracks:
            track = item.get('track')
            if track and track.get('album') and track.get('artists'):
                album_name = track['album']['name']
                artist_names = [artist['name'] for artist in track['artists']]
                # Join multiple artists with a comma for simplicity
                artist_string = ", ".join(artist_names)

                if (album_name, artist_string) not in unique_albums:
                    unique_albums.add((album_name, artist_string))
                    new_albums_found.append({'name': album_name, 'artist': artist_string})

        # Add newly found albums to the existing list
        current_albums.extend(new_albums_found)
        # Sort the albums for consistent output (optional)
        current_albums.sort(key=lambda x: (x['artist'].lower(), x['name'].lower()))

        save_albums(current_albums)
        return jsonify({'message': 'Playlist processed successfully', 'albums': current_albums}), 200

    except spotipy.exceptions.SpotifyException as se:
        print(f"Spotify API Error: {se}")
        return jsonify({'error': f'Spotify API Error: {se.msg}'}), se.http_status
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/get_albums', methods=['GET'])
def get_albums():
    """Returns the current list of stored albums."""
    albums = load_albums()
    return jsonify({'albums': albums}), 200

if __name__ == '__main__':
    # Ensure the albums file exists or is created empty on startup
    if not os.path.exists(ALBUMS_FILE):
        save_albums([])
    app.run(debug=True) # Run in debug mode for development
