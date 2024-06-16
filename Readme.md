# Merge YouTube Music Likes into Spotify

This project aims to synchronize your liked songs from YouTube Music to Spotify. The script fetches liked songs from YouTube Music and checks if they are already liked on Spotify. If not, it attempts to add them to your Spotify liked songs, ensuring no duplicates and handling rate limits gracefully.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Setup YouTube Music API Authentication](#setup-youtube-music-api-authentication)
- [Script Breakdown](#script-breakdown)
- [License](#license)

## Installation

1. Clone this repository:
    ```bash
    git clone https://github.com/yourusername/merge-youtube-likes-to-spotify.git
    cd merge-youtube-likes-to-spotify
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Place your Spotify credentials in a JSON file at `./Auth/spotify_credentials.json`:
    ```json
    {
        "client_id": "your_spotify_client_id",
        "client_secret": "your_spotify_client_secret",
        "redirect_uri": "your_spotify_redirect_uri"
    }
    ```

2. Authenticate with YouTube Music API and save headers:
    ```python
    from ytmusicapi import YTMusic
    YTMusic.setup(filepath='./Auth/headers_auth.json', open_browser=True)
    ```

3. Run the script:
    ```bash
    python merge_youtube_music_likes_into_spotify.py
    ```

## Setup YouTube Music API Authentication

To authenticate with the YouTube Music API, you need to perform an OAuth authentication and save the headers for future use. This step needs to be done only once:

1. Import the YTMusic module and run the setup:
    ```python
    from ytmusicapi import YTMusic
    YTMusic.setup(filepath='./Auth/headers_auth.json', open_browser=True)
    ```

2. This will open a browser window asking you to log in to your YouTube Music account and authorize the application. After completing this, the authentication headers will be saved to `./Auth/headers_auth.json`.

## Script Breakdown

The script is broken down into the following sections:

### Imports and Setup

The necessary libraries are imported, and display options for tabular data are set up.

### Loading Credentials

Spotify credentials are loaded from a JSON file.

### Fetching Liked Songs

Functions to fetch liked songs from YouTube Music and Spotify.

```python
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
```

### Cleaning Data

Functions to clean the list of songs by removing duplicates already present on Spotify and those previously added.

```python
def load_added_songs(added_songs_file):
    if os.path.exists(added_songs_file):
        with open(added_songs_file, 'r') as f:
            added_songs_list = json.load(f)
        successfully_added_songs = pd.DataFrame(added_songs_list)
    else:
        successfully_added_songs = pd.DataFrame(columns=['title', 'artist', 'album'])
    return successfully_added_songs

def clean_missing_songs(missing_songs, exclusion_songs):
    return missing_songs[~missing_songs.set_index(['title', 'artist']).index.isin(exclusion_songs.set_index(['title', 'artist']).index)]
```

### Adding Songs to Spotify

A function to add songs to Spotify and log the results immediately to ensure progress is saved.

```python
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
```

### Main Execution

The main script fetches data, cleans it, limits it, and then processes it.

```python
# Fetch the liked songs from YouTube and Spotify
youtube_likes_df = fetch_youtube_music_likes(ytmusic)
spotify_likes_df = fetch_spotify_likes(sp)

# Load previously added songs
added_songs_file = './data/added_songs_to_spotify.json'
successfully_added_songs = load_added_songs(added_songs_file)

# Calculate missing songs
missing_songs = clean_missing_songs(youtube_likes_df, spotify_likes_df)
missing_songs = clean_missing_songs(missing_songs, successfully_added_songs)

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
```

For the complete script, please refer to the [merge youtube Music likes into Spotify.py](merge_youtube_music_likes_into_spotify.py) file in this repository.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
