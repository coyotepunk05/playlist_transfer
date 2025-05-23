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
# This will still prompt twice due to Flask's reloader in debug mode.
# For production, consider using environment variables or a secure secret management system.
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

# --- Removed local file storage for albums.json ---
# The application will no longer store album data on the server's disk.

@app.route('/process_playlist', methods=['POST'])
def process_playlist():
    """
    Processes a Spotify playlist URL, extracts album and artist information,
    and returns the list of albums directly to the frontend.
    No data is stored on the server.
    """
    data = request.get_json()
    playlist_url = data.get('playlist_url')

    if not playlist_url:
        return jsonify({'error': 'No playlist URL provided'}), 400

    if not sp:
        return jsonify({'error': 'Spotify API not initialized or invalid credentials. Restart the app and provide valid credentials.'}), 500

    try:
        # Extract playlist ID from URL
        # Example URL: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
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

        extracted_albums = []
        unique_albums_set = set() # Use a set to track unique (album_name, artist_string) tuples

        for item in tracks:
            track = item.get('track')
            if track and track.get('album') and track.get('artists'):
                album_name = track['album']['name']
                artist_names = [artist['name'] for artist in track['artists']]
                artist_string = ", ".join(artist_names)

                # Add to unique set and list if not already present
                if (album_name, artist_string) not in unique_albums_set:
                    unique_albums_set.add((album_name, artist_string))
                    extracted_albums.append({'name': album_name, 'artist': artist_string})

        # Sort the albums for consistent output (optional)
        extracted_albums.sort(key=lambda x: (x['artist'].lower(), x['name'].lower()))

        # Return the extracted albums directly
        return jsonify({'message': 'Playlist processed successfully', 'albums': extracted_albums}), 200

    except spotipy.exceptions.SpotifyException as se:
        print(f"Spotify API Error: {se}")
        return jsonify({'error': f'Spotify API Error: {se.msg}'}), se.http_status
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# The /get_albums route is no longer needed as data is not stored on the server.

if __name__ == '__main__':
    # Set debug to False for a more production-like environment.
    # When debug=False, the reloader is off, preventing double prompts.
    app.run(debug=False)