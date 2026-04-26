# Repository Instructions

## Session Startup

At the start of a meaningful work session:

1. Read `docs/plans/current-status.md`.
2. Read `ROADMAP.md` when scope, sequencing, or long-term direction may change.
3. Read `docs/research/matching-research.md` before changing match policy.

## Core Safety Rule

This app can mutate a real Spotify library. Default to dry-run behavior.

- Do not call `current_user_saved_tracks_add` unless the user explicitly asks for a live write in the current session.
- The script defaults to dry-run. Live writes require `MUSICLIKESSYNC_WRITE_TO_SPOTIFY=1`.
- Any match with `review` or `rejected` status must not be written to Spotify.
- Preserve `data/match_results.json` and `data/dry_run_match_review.json` as review artifacts when investigating match quality.

## Matching Policy

- Prefer exact recording identifiers when available. ISRC is the best common identifier exposed by Spotify.
- Do not treat Spotify search rank as proof of identity.
- Use title, all artists, album, duration, ISRC, and ambiguity margin together.
- If metadata disagrees, return `review` or `rejected` instead of forcing a match.
- Different releases, remasters, live versions, covers, translations, and regional titles are acceptable only when evidence is strong enough for a same-recording match.

## Change Scope

- Prefer small, tested changes over notebook-sized edits.
- Keep pure matching logic in `music_likes_sync/` so it can be tested without credentials.
- Avoid unrelated refactors of the historical notebook/script unless required for safety.
- Do not commit ignored local auth, cache, virtualenv, notebook checkpoints, or generated data files.

## Testing And QA

- Add or update unit tests under `tests/` before changing match behavior.
- Run `python -m unittest discover -s tests -v` before claiming the matcher is safe.
- Run `python -m py_compile "merge youtube Music likes into Spotify.py" music_likes_sync\matching.py music_likes_sync\legacy.py music_likes_sync\review.py` after script integration changes.
- For real-world QA without writes, run `python -m music_likes_sync.review data\search_results.json --output data\dry_run_match_review.json`.

## Version Discipline

- Keep `ROADMAP.md` and `docs/plans/current-status.md` aligned with implemented scope.
- Split future backend, Docker, web UI, and auth work into separate versions.
- Commit tested slices with focused messages.
