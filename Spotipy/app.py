from flask import Flask, request, url_for, session, redirect, render_template
import spotipy
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
import time 
from time import gmtime, strftime
from credentials import CLIENT_ID, CLIENT_SECRET, SECRET_KEY, USERID
import os
app = Flask(__name__)

# Defining consts
TOKEN_CODE = "token_info"
MEDIUM_TERM = "medium_term"
SHORT_TERM = "short_term"
LONG_TERM = "long_term"
SCOPE = 'playlist-modify-public'



def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirectPage",_external=True), 
        scope='user-top-read user-library-read playlist-modify-public'
    )

def create_spotify_oauth1():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirectPage",_external=True), 
        scope=SCOPE
    )
    

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

def get_artist_id(artist_name):
    # Search for the artist by name
    results = sp.search(q='artist:' + artist_name, type='artist')
   
    # Get the first artist from the search results
    if results['artists']['items']:
        artist = results['artists']['items'][0]
        artist_id = artist['id']
        return artist_id
    else:
        print(f"Artist '{artist_name}' not found.")
        return "None"
        
def get_top_tracks(artist):
    results = sp.search(q=f'artist:{artist}', type='artist', limit=1)

    if results['artists']['items']:
        artist_id = results['artists']['items'][0]['id']
        top_tracks = sp.artist_top_tracks(artist_id)
        
        track_info_list = []
        for track in top_tracks['tracks'][:10]:
            track_name = track['name']
            track_url = track['external_urls']['spotify']

            # Retrieve album information to get the movie name
            album_id = track['album']['id']
            album_info = sp.album(album_id)
            movie_name = album_info['name']

            track_info_list.append({'track_name': track_name, 'track_url': track_url, 'movie_name': movie_name})

        return track_info_list
    else:
        return None

def get_reco_tracks(seed_artists):
    results = sp.recommendations(seed_artists=seed_artists)

    if results['artists']['items']:
        artist_id = results['artists']['items'][0]['id']
        top_tracks = sp.artist_top_tracks(artist_id)
        
        track_info_list = []
        for track in top_tracks['tracks'][:10]:
            track_name = track['name']
            track_url = track['external_urls']['spotify']

            # Retrieve album information to get the movie name
            album_id = track['album']['id']
            album_info = sp.album(album_id)
            movie_name = album_info['name']

            track_info_list.append({'track_name': track_name, 'track_url': track_url, 'movie_name': movie_name,'track_id': track_url.split('/')[-1].strip()})

        return track_info_list
    else:
        return None
        
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = 'PES Cookie'

@app.route('/')
def index():
    name = 'username'
    return render_template('index.html', title='Welcome', username=name)

@app.route('/home')
def home():
    return render_template('home.html')
    
@app.route('/login')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/redirect')
def redirectPage():
    sp_oauth = create_spotify_oauth()
    session.clear() 
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session[TOKEN_CODE] = token_info    
    return redirect(url_for("home", _external=True))


def get_token(): 
    token_info = session.get(TOKEN_CODE, None)
    if not token_info: 
        raise "exception"
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60 
    if (is_expired): 
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info 

@app.route('/tracks', methods=['GET', 'POST'])
def tracks():
    if request.method == 'POST':
        artist_name = request.form['artist']
        track_info_list = get_top_tracks(artist_name)
        artist_id = get_artist_id(artist_name)
        seed_artists = []
        seed_artists.append(artist_id)
        #track_info_list = get_reco_tracks(seed_artists)
        if track_info_list:
            return render_template('tracks.html', artist=artist_name, tracks=track_info_list)
        else:
            return render_template('tracks.html', error=f'No results found for artist: {artist_name}')

    return render_template('tracks.html', artist=None, tracks=None, error=None)
    
@app.route('/getTracks')
def getTracks():
    try: 
        token_info = get_token()
    except: 
        print("user not logged in")
        return redirect("/")
    sp1 = Spotify(
        auth=token_info['access_token'],
    )

    current_user_name = sp1.current_user()['display_name']

    short_term = sp1.current_user_top_tracks(
        limit=10,
        offset=0,
        time_range=SHORT_TERM,
    )
    medium_term = sp1.current_user_top_tracks(
        limit=10,
        offset=0,
        time_range=MEDIUM_TERM,
    )
    long_term = sp1.current_user_top_tracks(
        limit=10,
        offset=0,
        time_range=LONG_TERM,
    )

    if os.path.exists(".cache"): 
        os.remove(".cache")

    return render_template('receipt.html', user_display_name=current_user_name, short_term=short_term, medium_term=medium_term, long_term=long_term, currentTime=gmtime())


@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
    return strftime("%a, %d %b %Y", date)

@app.template_filter('mmss')
def _jinja2_filter_miliseconds(time, fmt=None):
    time = int(time / 1000)
    minutes = time // 60 
    seconds = time % 60 
    if seconds < 10: 
        return str(minutes) + ":0" + str(seconds)
    return str(minutes) + ":" + str(seconds ) 

@app.route('/albumsearch')
def albumsearch():
    return render_template('albumsearch.html')

@app.route('/search', methods=['POST'])
def search_spotify():
    album_name = request.form['album_name']
    artist_name = request.form['artist_name']

    # Search for the album using the provided name and artist
    results = sp.search(q=f"album:{album_name} artist:{artist_name}", type='album')
    items = results['albums']['items']

    if not items:
        return render_template('result.html', result_text="Album not found.")

    # Take the first album from the search results
    album = items[0]

    # Get the primary artist (owner of the album)
    primary_artist = album['artists'][0]['name']
    album_name = album['name']

    # Dictionary to store featured artists and the corresponding songs
    featured_artists = {}

    # Get the tracks of the album
    tracks = sp.album_tracks(album['id'])

    for item in tracks['items']:
        for artist_info in item['artists']:
            if 'name' in artist_info:
                artist_name = artist_info['name']
                if artist_name != primary_artist:  # Exclude songs by the primary artist
                    if artist_name not in featured_artists:
                        featured_artists[artist_name] = []
                    featured_artists[artist_name].append(item['name'])

    # Display the result in the HTML template
    result_text = f"Album: {album_name}<br>Primary Artist: {primary_artist}<br><br>"

    if featured_artists:
        result_text += "Featured Artists and Their Songs:<br>"
        for artist, songs in featured_artists.items():
            result_text += f"Featured Artist: {artist}<br>Songs:<br>"
            for song in songs:
                result_text += f"  - {song}<br>"
    else:
        result_text += "No featured artists found."

    return render_template('result.html', result_text=result_text)

@app.route('/create_playlist', methods=['GET','POST'])
def create_playlist():
    sp_oauth=create_spotify_oauth()
    token_info = sp_oauth.get_access_token(request.args.get('code'))
    spotifyObject = Spotify(auth=token_info['access_token'])
    playlists = spotifyObject.current_user_playlists()

    playlist_info = [(playlist['id'], playlist['name']) for playlist in playlists['items']]
    
    if request.method == 'POST':
        playlist_name = request.form['playlist_name']
        playlist_description = request.form['playlist_description']
        
        

        # Create a playlist
        playlist = spotifyObject.user_playlist_create(user=spotifyObject.me()['id'], name=playlist_name,
                                                      public=True, description=playlist_description)
        playlists = spotifyObject.current_user_playlists()
        playlist_info = [(playlist['id'], playlist['name']) for playlist in playlists['items']]
        return render_template('create_playlist.html', result_text=f"Playlist '{playlist_name}' created successfully!", playlists=playlist_info)
    
    return render_template('create_playlist.html', playlists=playlist_info)

@app.route('/add_tracks', methods=['POST'])
def add_tracks():
    playlist_id = request.form['playlist_id']
    track_uris = request.form.getlist('track_uris')
    sp_oauth=create_spotify_oauth()

    token_info = sp_oauth.get_access_token(request.args.get('code'))
    spotifyObject = Spotify(auth=token_info['access_token'])
    
    # Add tracks to the playlist
    spotifyObject.user_playlist_add_tracks(user=spotifyObject.me()['id'], playlist_id=playlist_id, tracks=track_uris)
    playlists = spotifyObject.current_user_playlists()
    playlist_info = [(playlist['id'], playlist['name']) for playlist in playlists['items']]
    return render_template('create_playlist.html', add_result=f"Tracks added to the playlist successfully!",playlists=playlist_info)

if __name__ == '__main__':
    app.run(debug=True)