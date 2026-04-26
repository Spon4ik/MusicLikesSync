# Matching Research

Date: 2026-04-26

## Findings

Spotify exposes `external_ids.isrc` on track objects, and Spotify Search supports an `isrc:` field filter. ISRC is therefore the best available exact identifier on the Spotify side.

MusicBrainz documents ISRC as an identifier for a distinct sound recording, not the abstract song/work. That is exactly the identity level this app needs: the same recording, not a cover, live version, remix, or unrelated track with the same title.

ytmusicapi `get_liked_songs()` returns playlist item metadata such as `videoId`, title, artists, album, duration, and like status via the playlist item shape. It does not provide ISRC in the documented liked-song payload, so YouTube Music liked tracks cannot be matched by a universal ID directly from YTM alone.

Existing projects converge on the same defensive pattern:

- `davidmalko87/ytmusic-to-spotify-sync` documents a three-pass strategy: ISRC exact match, normalized title and artist, then fuzzy fallback with duration validation. It also includes dry-run mode and unmatched tracking.
- `linsomniac/spotify_to_ytmusic` avoids blindly trusting search rank by first searching albums by artist and looking for exact track names; its README calls out that this is safer for short or ambiguous titles.
- `abhishekmj303/ytm2spt` exposes a dry-run mode for YouTube Music to Spotify playlist transfer.

## Recommended Identity Strategy

1. Use ISRC exact match when a trustworthy source ISRC exists.
2. Otherwise, search Spotify with normalized title and primary/all artists.
3. Score candidates with title, artist-token overlap, album similarity, and duration closeness.
4. Require a high automatic threshold and a clear margin over the second-best candidate.
5. Send all ambiguous or metadata-conflicting candidates to manual review.
6. Keep a dry-run artifact before live writes.

## Important Limits

There is no perfect universal ID available from YouTube Music liked songs via ytmusicapi. MusicBrainz can help enrich or validate candidates, especially through ISRC lookup, but it is not complete enough to be the only source of truth.

Because Spotify Liked Songs are personal library state, false positives are worse than missed matches. The app should prefer "review" over "selected" whenever evidence is incomplete.

## Sources

- Spotify Search API: https://developer.spotify.com/documentation/web-api/reference/search
- Spotify Track object: https://developer.spotify.com/documentation/web-api/reference/get-track
- MusicBrainz ISRC: https://musicbrainz.org/doc/ISRC
- MusicBrainz API ISRC lookup: https://musicbrainz.org/doc/MusicBrainz_API
- ytmusicapi reference: https://ytmusicapi.readthedocs.io/en/1.4.1/reference.html
- ytmusic-to-spotify-sync: https://github.com/davidmalko87/ytmusic-to-spotify-sync
- spotify_to_ytmusic: https://github.com/linsomniac/spotify_to_ytmusic
- ytm2spt: https://github.com/abhishekmj303/ytm2spt
