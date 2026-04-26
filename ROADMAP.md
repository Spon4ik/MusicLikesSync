# MusicLikesSync Roadmap

## v0.1 - Safety Baseline

Goal: prevent accidental Spotify writes from weak search matches.

Status: implemented in this branch.

- Extract conservative matching logic into `music_likes_sync/`.
- Add unit tests for featured artists, wrong artists, duration mismatches, ambiguous candidates, and ISRC exact matches.
- Make the historical script dry-run by default.
- Add offline review command for cached `data/search_results.json`.
- Add project instructions and research notes.

## v0.2 - Reviewable Sync CLI

Goal: make dry-run review the normal workflow.

- Add a first-class CLI command to fetch YTM likes, search Spotify, and generate a review file.
- Add CSV/HTML review output with selected, review, and rejected tabs.
- Add manual approval/deny overrides by Spotify ID.
- Add a live-write command that only writes approved or selected matches.
- Add an undo report for everything written.

## v0.3 - Metadata Enrichment

Goal: improve match confidence without becoming reckless.

- Preserve all YTM artists, `videoId`, album id, duration, and availability metadata.
- Store Spotify ISRC, duration, album type, release date, URL, and URI.
- Add optional MusicBrainz lookup for candidate validation and ISRC enrichment.
- Cache external lookups with clear source attribution and timestamps.

## v0.4 - Docker Backend

Goal: make the sync repeatable and deployable.

- Build a small backend service with durable storage for snapshots, matches, approvals, and write logs.
- Package with Docker Compose.
- Add rate-limit aware workers.
- Add secrets/config validation for Spotify and YouTube Music auth.

## v0.5 - Web UI

Goal: make match review practical.

- Add a web interface for auth setup, dry-run execution, and match review.
- Show side-by-side YTM and Spotify metadata.
- Support manual search and replacement for review/rejected rows.
- Require explicit confirmation before live writes.

## v1.0 - Reliable Liked Songs Migration

Goal: safe end-to-end migration from YouTube Music liked songs to Spotify Liked Songs.

- Default path is dry-run, review, approve, write.
- Live writes are idempotent and logged.
- Documentation covers setup, recovery, and limitations.
- QA includes real cached data and a small live canary batch approved by the user.
