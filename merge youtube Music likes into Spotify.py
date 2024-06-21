# merge YouTube Music likes into Spotify

# %% [markdown]
# ## imports

# %%
import json
import pandas as pd
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import difflib
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


# %%
def read_or_fetch_youtube_likes(ytmusic, file_path='data/youtube_likes.json'):
    """Read YouTube likes from a JSON file or fetch and save them if the file doesn't exist."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return pd.DataFrame(data)
    else:
        data = fetch_youtube_music_likes(ytmusic)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data.to_dict('records'), file, indent=4)
        return data

def read_or_fetch_spotify_likes(sp, file_path='data/spotify_likes.json'):
    """Read Spotify likes from a JSON file or fetch and save them if the file doesn't exist."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return pd.DataFrame(data)
    else:
        data = fetch_spotify_likes(sp)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data.to_dict('records'), file, indent=4)
        return data


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


# %%
import re
import unicodedata
from transliterate import translit

def normalize_text(text, language_code='ru'):
    """Normalize text for better matching by retaining Unicode characters, lowercasing, removing punctuation, and transliterating."""
    # Transliterate text
    transliterated_text = translit(text, language_code, reversed=True)
    # Normalize unicode characters to canonical form
    normalized_text = unicodedata.normalize('NFKC', transliterated_text)
    # Lowercase and strip trailing spaces
    normalized_text = normalized_text.lower().strip()
    # Remove punctuation
    normalized_text = re.sub(r'[^\w\s]', '', normalized_text)
    # Remove extra spaces
    normalized_text = re.sub(r'\s+', ' ', normalized_text)
    return normalized_text


# %%
def clean_missing_songs(missing_songs, reference_songs, ref_col_map=None):
    """
    Optimized function to exclude songs from missing_songs that have been successfully added to Spotify 
    or are already in the user's Spotify likes using a common normalization function.
    
    Parameters:
        missing_songs (pd.DataFrame): DataFrame of songs to be checked.
        reference_songs (pd.DataFrame): DataFrame of reference songs for comparison.
        ref_col_map (dict): Optional dictionary to map reference column names to missing_songs' column names.
        
    Returns:
        pd.DataFrame: Filtered DataFrame of missing songs.
    """
    if ref_col_map is None:
        ref_col_map = {'title': 'title', 'artist': 'artist'}

    # Check if the required columns exist
    if not all(col in missing_songs.columns for col in ['title', 'artist']) or \
       not all(col in reference_songs.columns for col in ref_col_map.values()):
        raise KeyError("Required columns are missing in the input DataFrames")

    # Normalize titles and artists for comparison
    for col in ['title', 'artist']:
        missing_songs[f'normalized_{col}'] = missing_songs[col].apply(normalize_text)
        reference_songs[f'normalized_{col}'] = reference_songs[ref_col_map[col]].apply(normalize_text)

    # Create an index of normalized titles and artists from reference songs for comparison
    reference_index = set(zip(reference_songs['normalized_title'], reference_songs['normalized_artist']))

    # Efficiently filter out songs that have been successfully added or are already in the user's Spotify likes
    mask = missing_songs.apply(lambda x: (x[f'normalized_title'], x[f'normalized_artist']) not in reference_index, axis=1)
    cleaned_songs = missing_songs.loc[mask].copy()

    # Drop the normalized columns before returning
    cleaned_songs.drop(columns=['normalized_title', 'normalized_artist'], inplace=True)
    reference_songs.drop(columns=['normalized_title', 'normalized_artist'], inplace=True)

    return cleaned_songs


# %% [markdown]
# ### Defining a functions to search songs in Spotify

# %%
import re
def extract_featured_artists(title):
    """Extract featured artists from the title if 'feat', 'ft.', or similar are found."""
    pattern = r"feat\.?|ft\.?|featuring"
    parts = re.split(pattern, title, flags=re.IGNORECASE)
    if len(parts) > 1:
        main_title = parts[0].strip()
        featured_artists = parts[1].strip().split(',')
        featured_artists = [artist.strip() for artist in featured_artists]
        return main_title, featured_artists
    return title, []


# %%
def query_spotify_for_tracks(sp, songs, max_results=50):
    all_search_results = []
    for song in songs:
        main_title, featured_artists = extract_featured_artists(song.get('normalized_title', ''))
        
        # Include featured artists in the artist string
        artist_query = f"{song.get('normalized_artist', '')} {' '.join(featured_artists)}".strip()

        queries = [
            f"{main_title} {song.get('normalized_artist', '')}",
            f"track:{main_title} artist:{song.get('normalized_artist', '')}",
            f"track:{main_title}",
            f"artist:{song.get('normalized_artist', '')} track:{main_title}",
            f"{main_title} {song.get('normalized_artist', '')} {song.get('album', '')}",
            f"{main_title} {artist_query}",
            f"track:{main_title} artist:{artist_query}",
            f"{main_title} {' '.join(featured_artists)}",
            f"track:{main_title} artist:{' '.join(featured_artists)}",
            f"{main_title} {artist_query} {' '.join(featured_artists)}",
            f"{main_title} {artist_query} {song.get('album', '')}"
        ]

        search_results = []
        for query in queries:
            if not query.strip():
                continue
            result = sp.search(q=query, limit=max_results, type='track')
            if result and 'tracks' in result and 'items' in result['tracks']:
                for track in result['tracks']['items']:
                    variant = {
                        'original_title': song.get('title', ''),  # Use original title
                        'original_artist': song.get('artist', ''),  # Use original artist
                        'original_album': song.get('album', ''),  # Use original album
                        'query_title': main_title,  # Use normalized and cleaned title
                        'query_artist': artist_query,  # Use normalized and combined artist string
                        'query_album': song.get('album', 'Unknown Album'),  # Use original album
                        'spotify_title': track['name'],
                        'spotify_artist': ', '.join(artist['name'] for artist in track['artists']),
                        'spotify_album': track['album']['name'],
                        'spotify_id': track['id']
                    }
                    search_results.append(variant)

        if search_results:  # Ensure there are search results before appending
            all_search_results.append({
                'title': song.get('title', ''),  # Use original title
                'artist': song.get('artist', ''),  # Use original artist
                'album': song.get('album', ''),  # Use original album
                'variants': search_results
            })

    # Optional: write results to a file or handle them as needed
    with open('data/search_results.json', 'w') as f:
        json.dump(all_search_results, f, indent=4)

    return all_search_results


# %%
import json
import difflib

def calculate_similarity(search_results):
    """Calculate similarity scores for each track variant."""
    for item in search_results:
        for variant in item['variants']:
            normalized_query_title = normalize_text(variant['query_title'])
            normalized_spotify_title = normalize_text(variant['spotify_title'])
            normalized_query_artist = normalize_text(variant['query_artist'])
            normalized_spotify_artist = normalize_text(variant['spotify_artist'])
            normalized_query_album = normalize_text(variant['query_album'])
            normalized_spotify_album = normalize_text(variant['spotify_album'])

            # Check for exact match between normalized query and result
            exact_match = (normalized_query_title == normalized_spotify_title and
                           normalized_query_artist == normalized_spotify_artist and
                           normalized_query_album == normalized_spotify_album)
            if exact_match:
                variant['similarity_score'] = 1.0
            else:
                title_score = difflib.SequenceMatcher(None, normalized_query_title, normalized_spotify_title).ratio()
                artist_score = difflib.SequenceMatcher(None, normalized_query_artist, normalized_spotify_artist).ratio()
                album_score = difflib.SequenceMatcher(None, normalized_query_album, normalized_spotify_album).ratio()

                # Calculate the weighted average of the scores
                variant['similarity_score'] = 0.4 * title_score + 0.4 * artist_score + 0.2 * album_score

    return search_results



# %%
def determine_best_matches(search_results):
    """Determine the best match for each track and store results in JSON."""
    best_matches = []
    for item in search_results:
        best_match = max(item['variants'], key=lambda x: x['similarity_score'], default={'similarity_score': 0})
        best_matches.append({
            "original_title": item['title'],
            "original_artist": item['artist'],
            "original_album": item['album'],
            "best_variant": best_match,
            "status": "selected" if best_match['similarity_score'] > 0.75 else "not selected",
            "reason": "High similarity score" if best_match['similarity_score'] > 0.75 else "No match above threshold"
        })

    # Store the best matches in a JSON file for further processing
    with open('data/match_results.json', 'w') as f:
        json.dump(best_matches, f, ensure_ascii=False, indent=4)

    return best_matches



# %% [markdown]
# ### Defining a functions to add songs to Spotify

# %%
import logging
import os

# Configure logging
logging.basicConfig(filename='migration.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_tracks_to_spotify(sp):
    """Add selected tracks to Spotify from best matches and log each attempt."""
    try:
        with open('data/match_results.json', 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        # Load existing results if the file exists
        if os.path.exists('data/added_songs_to_spotify.json'):
            with open('data/added_songs_to_spotify.json', 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results = []

        for match in matches:
            if match['status'] == 'selected' and match['best_variant'].get('spotify_id'):
                try:
                    response = sp.current_user_saved_tracks_add(tracks=[match['best_variant']['spotify_id']])
                    status = 'added' if response is None else 'failed'
                    reason = 'Successfully added' if response is None else 'Failed to add'
                    logging.info(f"Added: {match['original_title']} by {match['original_artist']} - {reason}")
                except Exception as e:
                    status = 'failed'
                    reason = str(e)
                    logging.error(f"Failed to add: {match['original_title']} by {match['original_artist']} - {reason}")
            else:
                status = 'not attempted'
                reason = 'Track not selected due to low similarity score or missing Spotify ID'
                logging.warning(f"Not attempted: {match['original_title']} by {match['original_artist']} - {reason}")

            # Prepare the log entry
            log_entry = {
                "original_title": match['original_title'],
                "original_artist": match['original_artist'],
                "original_album": match['original_album'],
                "query_title": match['best_variant'].get('query_title'),
                "query_artist": match['best_variant'].get('query_artist'),
                "query_album": match['best_variant'].get('query_album'),
                "spotify_title": match['best_variant'].get('spotify_title'),
                "spotify_artist": match['best_variant'].get('spotify_artist'),
                "spotify_album": match['best_variant'].get('spotify_album'),
                "spotify_id": match['best_variant'].get('spotify_id'),
                "similarity_score": match['best_variant'].get('similarity_score', 0),  # Ensure default if not available
                "status": status,
                "reason": reason
            }

            if status != 'not attempted':
                results.append(log_entry)

        # Log the results to a JSON file
        with open('data/added_songs_to_spotify.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    except FileNotFoundError:
        logging.error("Match results file not found.")
    except Exception as e:
        logging.error(f"Failed to add tracks: {e}")


# %% [markdown]
# # Main Execution

# %%
# Main process
youtube_likes = read_or_fetch_youtube_likes(ytmusic).drop_duplicates()
spotify_likes = read_or_fetch_spotify_likes(sp)

# Print column names to debug
# print("YouTube Likes Columns:", youtube_likes.columns)
# print("Spotify Likes Columns:", spotify_likes.columns)

# Clean missing songs against Spotify likes
missing_songs_cleaned = clean_missing_songs(youtube_likes, spotify_likes)

# Load previously added songs
added_songs_file = './data/added_songs_to_spotify.json'
successfully_added_songs = load_added_songs(added_songs_file)

# Print column names to debug
# print("Missing Songs Cleaned Columns:", missing_songs_cleaned.columns)
# print("Successfully Added Songs Columns:", successfully_added_songs.columns)

# Clean missing songs against successfully added songs
ref_col_map = {
    'title': 'original_title',
    'artist': 'original_artist'
}
missing_songs_final = clean_missing_songs(missing_songs_cleaned, successfully_added_songs, ref_col_map)

# Ensure normalization is done before querying
missing_songs_final.loc[:, 'normalized_title'] = missing_songs_final['title'].apply(normalize_text)
missing_songs_final.loc[:, 'normalized_artist'] = missing_songs_final['artist'].apply(normalize_text)


# %%
# Search
search_results = query_spotify_for_tracks(sp, missing_songs_final.head(100).to_dict('records'))
search_results_with_scores = calculate_similarity(search_results)
best_matches = determine_best_matches(search_results_with_scores)


# %%
# Proceed to add tracks to Spotify using these best matches
add_tracks_to_spotify(sp)
