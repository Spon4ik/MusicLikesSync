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
import difflib
import time
import os

# %% [markdown]
# # Load credentials

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
# # Load ytmusic liked

# %% [markdown]
# ## sample

# %%
# liked_song = ytmusic.get_liked_songs(limit=1)

# # Store the fetched data into a JSON file
# with open('./data/liked_songs_sample.json', 'w') as outfile:
#     json.dump(liked_song, outfile, indent=4)

# %% [markdown]
# ## defining a functio to fetch an All Liked tracks

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
# # Defining a function to Fetch liked songs from Spotify

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
                'album': track['album']['name'],
                'spotify_id': track['id']
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


# %%
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
# # Load already added tracks from history run

# %%
# Load previously added songs from JSON file if it exists
def load_added_songs(added_songs_file):
    if os.path.exists(added_songs_file):
        with open(added_songs_file, 'r') as f:
            added_songs_list = json.load(f)
        successfully_added_songs = pd.DataFrame(added_songs_list)
    else:
        successfully_added_songs = pd.DataFrame(columns=['title', 'artist', 'album', 'spotify_id'])

    if 'spotify_id' not in successfully_added_songs.columns:
        successfully_added_songs['spotify_id'] = []

    return successfully_added_songs


# %% [markdown]
# # Normalization

# %% [markdown]
# ## process featured artists in titles

# %%
import re
def extract_featured_artists(title):
    """Extract featured artists from the title if 'feat', 'ft.', or similar are found."""
    # Improved pattern to match 'feat' or 'ft.' only when followed by artists
    pattern = r"\s\((feat\.?|ft\.?|freq\.?|featuring)\s+(.+?)\)$"
    match = re.search(pattern, title, re.IGNORECASE)
    if match:
        main_title = title[:match.start()].strip()
        featured_artists = match.group(2).split(',')
        featured_artists = [artist.strip() for artist in featured_artists]
        return main_title, featured_artists
    return title, []


# %%
from deep_translator import GoogleTranslator

# Replace the existing translator initialization with deep-translator
# translator = Translator()  # Remove this line

def test_translation(text, src_lang):
    try:
        translated_text = GoogleTranslator(source=src_lang, target='en').translate(text)
        return translated_text
    except Exception as e:
        return f"Translation error for text '{text}': {e}"


# %%
import re
import unicodedata
from transliterate import translit, get_available_language_codes


# %%
from googletrans import Translator

translator = Translator()

def detect_language(text):
    if re.search('[\u0590-\u05FF]', text):  # Hebrew range
        return 'he'
    elif re.search('[\u0400-\u04FF]', text):  # Russian range
        return 'ru'
    else:
        return 'en'  # Default to English


# %%
def strip_suffixes(text):
    """Remove common suffixes such as ' - Original Mix' or ' - Remix'."""
    return re.sub(r' - (Original Mix|Remix|Edit|Version|Extended Mix|Instrumental)$', '', text, flags=re.IGNORECASE)


# %% [markdown]
# ## normalize_text

# %%
def normalize_text(text, transliterate_flag=False, translate_flag=False):
    """Normalize text for better matching by retaining Unicode characters, lowercasing, removing punctuation, and optionally transliterating and translating."""
    text = strip_suffixes(text)
    language_code = detect_language(text)
    
    try:
        if transliterate_flag and language_code in get_available_language_codes():
            # Transliterate text if the flag is set
            transliterated_text = translit(text, language_code, reversed=True)
        else:
            transliterated_text = text  # Use the original text if not transliterating
    except Exception as e:
        transliterated_text = text  # Fallback to original text if transliteration fails
        print(f"Transliteration error for text '{text}': {e}")

    translated_text = transliterated_text
    if translate_flag and language_code != 'en':
        try:
            translated_text = GoogleTranslator(source='iw' if language_code == 'he' else language_code, target='en').translate(transliterated_text)
        except Exception as e:
            print(f"Translation error for text '{text}': {e}")

    # Normalize unicode characters to canonical form
    normalized_text = unicodedata.normalize('NFKC', translated_text)
    # Lowercase and strip trailing spaces
    normalized_text = normalized_text.lower().strip()
    # Remove punctuation
    normalized_text = re.sub(r'[^\w\s]', '', normalized_text)
    # Remove extra spaces
    normalized_text = re.sub(r'\s+', ' ', normalized_text)
    return normalized_text


# %% [markdown]
# # clean_missing_songs

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
# # Defining a functions to search songs in Spotify

# %% [markdown]
# ## generate_queries

# %%
def generate_queries(normalized_title, normalized_artist, normalized_album, featured_artists):
    queries = []

    # Ensure featured_artists is a list
    if not isinstance(featured_artists, list):
        featured_artists = [featured_artists]

    # Concatenate featured artists to the main artist
    all_artists = normalized_artist
    if featured_artists:
        all_artists += ' ' + ' '.join(featured_artists)
    
    # Base query with title and artist
    base_query = f"track:{normalized_title} artist:{all_artists}"
    queries.append(base_query)

    # Query with featured artists in the title
    if featured_artists:
        title_with_feat = f"{normalized_title} (feat. {' '.join(featured_artists)})"
        queries.append(f"track:{title_with_feat} artist:{normalized_artist}")
    
    # Queries with album if it exists
    if normalized_album:
        queries.append(f"{base_query} album:{normalized_album}")
        if featured_artists:
            queries.append(f"track:{title_with_feat} artist:{normalized_artist} album:{normalized_album}")

            # Special case: featured artist in all fields
            album_with_feat = f"{normalized_album} (feat. {' '.join(featured_artists)})"
            queries.append(f"track:{normalized_title} artist:{all_artists} album:{album_with_feat}")
            queries.append(f"track:{title_with_feat} artist:{all_artists} album:{normalized_album}")
            queries.append(f"track:{title_with_feat} artist:{all_artists} album:{album_with_feat}")

    return queries


# %%
queries = generate_queries("wicked games", "parra for cuva", "wicked games", "anna naklab")
queries

# %% [markdown]
# ## query_spotify_for_tracks

# %%
def query_spotify_for_tracks(sp, songs, max_results=50):
    all_search_results = []
    for song in songs:
        main_title, featured_artists = extract_featured_artists(song.get('title', ''))
        
        normalized_title = normalize_text(main_title, transliterate_flag=False)
        normalized_artist = normalize_text(song.get('artist', ''), transliterate_flag=True, translate_flag=True)
        normalized_album = normalize_text(song.get('album', '')) if song.get('album', 'Unknown Album') != 'Unknown Album' else None

        # Normalize featured artists
        normalized_featured_artists = [normalize_text(artist, transliterate_flag=True, translate_flag=True) for artist in featured_artists]

        # Generate queries using the external function
        queries = generate_queries(normalized_title, normalized_artist, normalized_album, normalized_featured_artists)

        search_results = []
        for query in queries:
            # Append the query details to search_results initially
            search_results.append({
                'original_title': song.get('title', ''),
                'original_artist': song.get('artist', ''),
                'original_album': song.get('album', ''),
                'query_title': normalized_title,
                'query_artist': normalized_artist,
                'query_album': normalized_album if normalized_album else 'Unknown Album',
                'spotify_title': '',
                'spotify_artist': '',
                'spotify_album': '',
                'spotify_id': ''
            })

            result = sp.search(q=query, limit=max_results, type='track')
            if result and 'tracks' in result and 'items' in result['tracks']:
                for track in result['tracks']['items']:
                    variant = {
                        'original_title': song.get('title', ''),  # Use original title
                        'original_artist': song.get('artist', ''),  # Use original artist
                        'original_album': song.get('album', ''),  # Use original album
                        'query_title': normalized_title,  # Use normalized title
                        'query_artist': normalized_artist,  # Use normalized artist
                        'query_album': normalized_album if normalized_album else 'Unknown Album',  # Use normalized album or None
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

# %% [markdown]
# # calculate_similarity

# %%
import json
import difflib


# %%
def calculate_similarity(search_results):
    """Calculate similarity scores for each track variant."""
    for item in search_results:
        for variant in item['variants']:
            normalized_query_title = normalize_text(variant['query_title'])
            normalized_spotify_title = normalize_text(variant['spotify_title'])
            normalized_query_artist = normalize_text(variant['query_artist'], transliterate_flag=True)
            normalized_spotify_artist = normalize_text(variant['spotify_artist'], transliterate_flag=True)

            # Check if the original data has an album
            original_album_exists = item['album'] != 'Unknown Album'

            if not original_album_exists:
                title_score = difflib.SequenceMatcher(None, normalized_query_title, normalized_spotify_title).ratio()
                artist_score = difflib.SequenceMatcher(None, normalized_query_artist, normalized_spotify_artist).ratio()
                variant['similarity_score'] = 0.5 * title_score + 0.5 * artist_score
            else:
                normalized_query_album = normalize_text(variant['query_album'])
                normalized_spotify_album = normalize_text(variant['spotify_album'])
                title_score = difflib.SequenceMatcher(None, normalized_query_title, normalized_spotify_title).ratio()
                artist_score = difflib.SequenceMatcher(None, normalized_query_artist, normalized_spotify_artist).ratio()
                album_score = difflib.SequenceMatcher(None, normalized_query_album, normalized_spotify_album).ratio()
                variant['similarity_score'] = 0.4 * title_score + 0.4 * artist_score + 0.2 * album_score

    return search_results


# %% [markdown]
# # determine_best_matches

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
            "status": "selected" if best_match['similarity_score'] > 0.8 else "not selected",
            "reason": "High similarity score" if best_match['similarity_score'] >= 0.8 else "No match above threshold"
        })

    # Store the best matches in a JSON file for further processing
    with open('data/match_results.json', 'w') as f:
        json.dump(best_matches, f, ensure_ascii=False, indent=4)

    return best_matches



# %% [markdown]
# # Defining a functions to add songs to Spotify

# %%
def check_if_already_added(spotify_id, added_songs_df):
    """Check if a track with the given spotify_id is already in the added songs list."""
    if 'spotify_id' not in added_songs_df.columns:
        return False
    return spotify_id in added_songs_df['spotify_id'].values


# %%
import logging
import os

# Configure logging
logging.basicConfig(filename='migration.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# %%
import time
import logging

def add_tracks_to_spotify(sp, successfully_added_songs):
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
            spotify_id = match['best_variant'].get('spotify_id')
            if match['status'] == 'selected' and spotify_id:
                if not check_if_already_added(spotify_id, successfully_added_songs):
                    try:
                        response = sp.current_user_saved_tracks_add(tracks=[spotify_id])
                        status = 'added' if response is None else 'failed'
                        reason = 'Successfully added' if response is None else 'Failed to add'
                        logging.info(f"Added: {match['original_title']} by {match['original_artist']} - {reason}")
                        time.sleep(1)  # Delay to handle rate limits
                    except Exception as e:
                        status = 'failed'
                        reason = str(e)
                        logging.error(f"Failed to add: {match['original_title']} by {match['original_artist']} - {reason}")
                        if "API rate limit exceeded" in str(e):
                            print("API rate limit exceeded, pausing for 30 seconds...")
                            time.sleep(30)
                            # Optionally, retry the failed operation
                else:
                    status = 'not added'
                    reason = 'Track already added'
                    logging.info(f"Already added: {match['original_title']} by {match['original_artist']} - {reason}")
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
                "spotify_id": spotify_id,
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
missing_songs_final['normalized_title'] = missing_songs_final['title'].apply(lambda x: normalize_text(x, transliterate_flag=False))
missing_songs_final['normalized_artist'] = missing_songs_final['artist'].apply(lambda x: normalize_text(x, transliterate_flag=True, translate_flag=True))
missing_songs_final['normalized_album'] = missing_songs_final['album'].apply(lambda x: normalize_text(x, transliterate_flag=False) if x != 'Unknown Album' else None)



# %%
# missing_songs_final

# %%
# Search
search_results = query_spotify_for_tracks(sp, missing_songs_final.head(10000).to_dict('records'))
search_results_with_scores = calculate_similarity(search_results)
best_matches = determine_best_matches(search_results_with_scores)


# %%
# Proceed to add tracks to Spotify using these best matches
successfully_added_songs = load_added_songs(added_songs_file)
add_tracks_to_spotify(sp, successfully_added_songs)
