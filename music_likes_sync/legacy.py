"""Adapters for the original script's JSON-shaped search results."""

from __future__ import annotations

from typing import Any
import re

from music_likes_sync.matching import (
    MatchDecision,
    SpotifyCandidate,
    TrackIdentity,
    choose_best_match,
    split_artists,
)


def parse_duration_seconds(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return float(text)
    parts = text.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return float(total) if total > 0 else None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _source_from_item(item: dict[str, Any]) -> TrackIdentity:
    return TrackIdentity(
        title=str(item.get("title") or item.get("original_title") or ""),
        artists=split_artists(item.get("artist") or item.get("original_artist") or ""),
        album=str(item.get("album") or item.get("original_album") or ""),
        duration_seconds=parse_duration_seconds(
            item.get("duration_seconds") or item.get("duration")
        ),
        isrc=str(item.get("isrc") or item.get("source_isrc") or ""),
        source_id=str(item.get("videoId") or item.get("video_id") or item.get("source_id") or ""),
    )


def _candidate_from_variant(variant: dict[str, Any]) -> SpotifyCandidate:
    return SpotifyCandidate(
        title=str(variant.get("spotify_title") or variant.get("name") or ""),
        artists=split_artists(variant.get("spotify_artist") or variant.get("artists") or ""),
        album=str(variant.get("spotify_album") or ""),
        duration_ms=_int_or_none(
            variant.get("spotify_duration_ms") or variant.get("duration_ms")
        ),
        isrc=str(variant.get("spotify_isrc") or variant.get("isrc") or ""),
        spotify_id=str(variant.get("spotify_id") or variant.get("id") or ""),
        uri=str(variant.get("spotify_uri") or variant.get("uri") or ""),
        popularity=int(variant.get("spotify_popularity") or variant.get("popularity") or 0),
    )


def _find_variant(
    variants: list[dict[str, Any]],
    decision: MatchDecision,
) -> dict[str, Any]:
    candidate = decision.candidate
    if candidate:
        for variant in variants:
            if candidate.spotify_id and str(variant.get("spotify_id") or variant.get("id") or "") == candidate.spotify_id:
                return dict(variant)
            if candidate.uri and str(variant.get("spotify_uri") or variant.get("uri") or "") == candidate.uri:
                return dict(variant)

    if decision.scores:
        best_candidate = decision.scores[0].candidate
        for variant in variants:
            if best_candidate.spotify_id and str(variant.get("spotify_id") or variant.get("id") or "") == best_candidate.spotify_id:
                return dict(variant)

    return {}


def decide_legacy_item(item: dict[str, Any]) -> dict[str, Any]:
    variants = [dict(variant) for variant in item.get("variants", [])]
    source = _source_from_item(item)
    candidates = [_candidate_from_variant(variant) for variant in variants]
    decision = choose_best_match(source, candidates)
    best_variant = _find_variant(variants, decision)

    if best_variant:
        best_variant["similarity_score"] = decision.confidence
        best_variant["match_method"] = decision.method

    title = source.title
    artist = ", ".join(source.artists)
    reason = "; ".join(decision.reasons)
    reason = re.sub(r"\s+", " ", reason).strip()

    return {
        "original_title": title,
        "original_artist": artist,
        "original_album": source.album,
        "best_variant": best_variant,
        "status": decision.status.value,
        "reason": reason,
        "confidence": decision.confidence,
        "match_method": decision.method,
        "candidate_count": len([candidate for candidate in candidates if candidate.spotify_id or candidate.uri]),
    }
