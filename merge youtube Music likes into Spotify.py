# %% [markdown]
# # merge YouTube Music likes into Spotify

# %% [markdown]
# ## imports

# %%
import json
import pandas as pd
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os


# %% [markdown]
# ## setup display tabular

# %%
from itables import show, init_notebook_mode
init_notebook_mode(all_interactive=True)
import itables.options as opt
opt.lengthMenu = [2, 5, 10, 20, 50,100,200,500]

# %% [markdown]
# ## Load credentials

# %%
# Load Spotify credentials from JSON file
with open('./Auth/spotify_credentials.json') as f:
    spotify_credentials = json.load(f)

# # YouTube Music API Authentication
# ytmusic = ytmusicapi.setup_oauth(open_browser=True)

# YouTube Music API Authentication
# ytmusicapi.setup_oauth(filepath='./Auth/headers_auth.json', open_browser=True)
# YouTube Music API Authentication using the saved headers
ytmusic = YTMusic('./Auth/headers_auth.json')


# %%
# Spotify API Authentication
scope = "user-library-read user-library-modify"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_credentials['client_id'],
                                               client_secret=spotify_credentials['client_secret'],
                                               redirect_uri=spotify_credentials['redirect_uri'],
                                               scope=scope))


# %% [markdown]
# ## Load ytmusic liked

# %% [markdown]
# ### sample

# %%
# liked_song = ytmusic.get_liked_songs(limit=1)

# # Store the fetched data into a JSON file
# with open('./data/liked_songs_sample.json', 'w') as outfile:
#     json.dump(liked_song, outfile, indent=4)

# %% [markdown]
# ### defining a functio to fetch an All Liked tracks

# %%
# Fetch liked songs from YouTube Music
def fetch_youtube_music_likes(ytmusic):
    liked_songs = ytmusic.get_liked_songs(limit=10000)
    songs = []
    for song in liked_songs['tracks']:
        title = song.get('title', 'Unknown Title')
        artist_name = song['artists'][0]['name'] if song.get('artists') and len(song['artists']) > 0 else 'Unknown Artist'
        album = song.get('album')
        album_name = album['name'] if album else 'Unknown Album'
        
        songs.append({
            'title': title,
            'artist': artist_name,
            'album': album_name
        })
    return pd.DataFrame(songs)

# %% [markdown]
# ## Defining a function to Fetch liked songs from Spotify

# %%
# Fetch liked songs from Spotify
def fetch_spotify_likes(sp):
    results = sp.current_user_saved_tracks()
    songs = []
    while results:
        for item in results['items']:
            track = item['track']
            songs.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name']
            })
        if results['next']:
            results = sp.next(results)
        else:
            results = None
    return pd.DataFrame(songs)


# %% [markdown]
# ### Defining a functions to clean already added tracks to spotify to prevent from another atempt to ad them

# %%
# Load previously added songs from JSON file if it exists
def load_added_songs(added_songs_file):
    if os.path.exists(added_songs_file):
        with open(added_songs_file, 'r') as f:
            added_songs_list = json.load(f)
        successfully_added_songs = pd.DataFrame(added_songs_list)
    else:
        successfully_added_songs = pd.DataFrame(columns=['title', 'artist', 'album'])
    return successfully_added_songs

# Clean the missing songs by excluding those present in another DataFrame
def clean_missing_songs(missing_songs, exclusion_songs):
    return missing_songs[~missing_songs.set_index(['title', 'artist']).index.isin(exclusion_songs.set_index(['title', 'artist']).index)]



# %% [markdown]
# ### Defining a functions to add songs to Spotify

# %%
# Function to add songs to Spotify and log the response status
def add_songs_to_spotify(sp, songs, added_songs_file):
    results = []
    response_samples = []

    # Load previously added songs
    successfully_added_songs = load_added_songs(added_songs_file)

    failed_songs = pd.DataFrame(columns=['title', 'artist', 'album', 'status', 'reason'])

    for _, song in songs.iterrows():
        query = f"{song['title']} {song['artist']} {song['album']}"
        print(f"Searching for: {query}")
        result = sp.search(q=query, limit=1, type='track')
        if result['tracks']['items']:
            track_id = result['tracks']['items'][0]['id']
            try:
                response = sp.current_user_saved_tracks_add(tracks=[track_id])
                response_status = 'added' if response is None else 'failed'
                response_reason = 'Successfully added' if response is None else response
                results.append({**song, 'status': response_status, 'reason': response_reason})
                successfully_added_songs = pd.concat([successfully_added_songs, pd.DataFrame([{**song, 'status': response_status, 'reason': response_reason}])]).drop_duplicates()
            except spotipy.SpotifyException as e:
                if '429' in str(e):  # Rate limit error
                    print("Rate limit hit, sleeping for 60 seconds")
                    time.sleep(60)  # Wait for 60 seconds before retrying
                print(f"Failed to add {song['title']} by {song['artist']} to Spotify: {e}")
                results.append({**song, 'status': 'failed', 'reason': str(e)})
                failed_songs = pd.concat([failed_songs, pd.DataFrame([{**song, 'status': 'failed', 'reason': str(e)}])]).drop_duplicates()
        else:
            print(f"Could not find {song['title']} by {song['artist']} on Spotify")
            results.append({**song, 'status': 'failed', 'reason': 'not found'})
            failed_songs = pd.concat([failed_songs, pd.DataFrame([{**song, 'status': 'failed', 'reason': 'not found'}])]).drop_duplicates()
        
        # Collecting samples for responses
        response_samples.append(results[-1])
        
        # Print samples of different responses so far
        print("API Response Sample (up to current point):")
        for sample in response_samples:
            print(sample)
        
        # Update JSON files immediately
        added_songs_list = successfully_added_songs.to_dict(orient='records')
        with open(added_songs_file, 'w') as f:
            json.dump(added_songs_list, f, indent=4)

        failed_songs_list = failed_songs.to_dict(orient='records')
        with open('./data/failed_songs_to_spotify.json', 'w') as f:
            json.dump(failed_songs_list, f, indent=4)

    return pd.DataFrame(results)


# %% [markdown]
# # Main Execution

# %%
# Main Execution

# Fetch the liked songs from YouTube and Spotify
youtube_likes_df = fetch_youtube_music_likes(ytmusic)
spotify_likes_df = fetch_spotify_likes(sp)


# %%
# Load previously added songs
added_songs_file = './data/added_songs_to_spotify.json'
successfully_added_songs = load_added_songs(added_songs_file)


# %%

# Calculate missing songs
missing_songs = clean_missing_songs(youtube_likes_df, spotify_likes_df)
missing_songs


# %%
missing_songs = clean_missing_songs(missing_songs, successfully_added_songs)
missing_songs


# %%
# Apply the limit to the DataFrame
limit = 10 # 10 is only to see it run well, adjust as to any amount for complete sync
limited_missing_songs = missing_songs.head(limit)

# Check if there are remaining missing songs before running add_songs_to_spotify
if not limited_missing_songs.empty:
    # Add missing songs to Spotify and log the results
    results_df = add_songs_to_spotify(sp, limited_missing_songs, added_songs_file)

    print("Remaining missing songs have been saved to 'remaining_missing_songs.json'.")
else:
    print("No remaining missing songs to process.")
    with open('./data/failed_songs_to_spotify.json', 'w') as f:
        json.dump([], f, indent=4)


