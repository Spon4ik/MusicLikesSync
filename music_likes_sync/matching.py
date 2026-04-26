"""Conservative track matching for YouTube Music to Spotify syncs."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
import html
import re
import unicodedata


class MatchStatus(str, Enum):
    SELECTED = "selected"
    REVIEW = "review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TrackIdentity:
    title: str
    artists: list[str] = field(default_factory=list)
    album: str = ""
    duration_seconds: float | None = None
    isrc: str = ""
    source_id: str = ""


@dataclass(frozen=True)
class SpotifyCandidate:
    title: str
    artists: list[str] = field(default_factory=list)
    album: str = ""
    duration_ms: int | None = None
    isrc: str = ""
    spotify_id: str = ""
    uri: str = ""
    popularity: int = 0


@dataclass(frozen=True)
class CandidateScore:
    candidate: SpotifyCandidate
    score: float
    title_score: float
    artist_score: float
    album_score: float
    duration_score: float
    hard_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class MatchDecision:
    status: MatchStatus
    confidence: float
    method: str
    candidate: SpotifyCandidate | None = None
    reasons: tuple[str, ...] = ()
    scores: tuple[CandidateScore, ...] = ()


_FEATURE_RE = re.compile(
    r"(?:\(|\[|\s+-\s+|\s+)(?:feat\.?|ft\.?|featuring|with)\s+([^\)\]\-]+)(?:\)|\])?",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(
    r"\s*(?:\(|\[|\s+-\s+)"
    r"(?:official\s+(?:audio|video)|lyrics?|audio|video|radio\s+edit|edit|"
    r"single\s+version|album\s+version|original\s+mix|extended\s+mix|"
    r"remaster(?:ed)?(?:\s+\d{4})?|live|remix|instrumental)"
    r"(?:\)|\])?\s*$",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_ISRC_RE = re.compile(r"[^A-Z0-9]")


def normalize_isrc(isrc: str) -> str:
    return _ISRC_RE.sub("", (isrc or "").upper())


def normalize_text(text: str) -> str:
    """Normalize text for comparison without translating it."""
    text = html.unescape(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = text.replace("&", " and ")
    text = _VERSION_RE.sub("", text)
    text = re.sub(r"['’`]", "", text)
    words = _WORD_RE.findall(text)
    return " ".join(words)


def extract_featured_artists(title: str) -> tuple[str, list[str]]:
    """Return title without feat clauses plus artists mentioned in those clauses."""
    featured: list[str] = []

    def remember(match: re.Match[str]) -> str:
        raw = match.group(1) or ""
        featured.extend(split_artists(raw))
        return " "

    cleaned = _FEATURE_RE.sub(remember, title or "")
    return normalize_text(cleaned), featured


def split_artists(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        values = [str(item) for item in value]
    else:
        values = [str(value)]

    artists: list[str] = []
    for item in values:
        for part in re.split(r"\s*(?:,|;|/|\+|&|\band\b|\bx\b|\bvs\.?\b)\s*", item, flags=re.IGNORECASE):
            normalized = normalize_text(part)
            if normalized:
                artists.append(normalized)
    return artists


def _artist_tokens(title: str, artists: list[str]) -> set[str]:
    _, featured = extract_featured_artists(title)
    names = split_artists(artists) + split_artists(featured)
    tokens: set[str] = set()
    for name in names:
        tokens.add(name)
        tokens.update(_WORD_RE.findall(name))
    return {token for token in tokens if len(token) > 1}


def _similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _artist_overlap(source: TrackIdentity, candidate: SpotifyCandidate) -> float:
    source_tokens = _artist_tokens(source.title, source.artists)
    candidate_tokens = _artist_tokens(candidate.title, candidate.artists)
    if not source_tokens or not candidate_tokens:
        return 0.5
    return len(source_tokens & candidate_tokens) / len(source_tokens)


def _duration_parts(
    source_seconds: float | None,
    candidate_ms: int | None,
) -> tuple[float, bool]:
    if not source_seconds or not candidate_ms:
        return 0.7, False
    candidate_seconds = candidate_ms / 1000.0
    tolerance = max(8.0, source_seconds * 0.05)
    difference = abs(source_seconds - candidate_seconds)
    if difference <= tolerance:
        return 1.0, False
    if difference <= tolerance * 2:
        return 0.35, True
    return 0.0, True


def score_candidate(source: TrackIdentity, candidate: SpotifyCandidate) -> CandidateScore:
    source_title, _ = extract_featured_artists(source.title)
    candidate_title, _ = extract_featured_artists(candidate.title)
    title_score = _similarity(source_title, candidate_title)
    artist_score = _artist_overlap(source, candidate)
    album_score = _similarity(normalize_text(source.album), normalize_text(candidate.album))
    duration_score, duration_mismatch = _duration_parts(
        source.duration_seconds,
        candidate.duration_ms,
    )

    score = (
        title_score * 0.42
        + artist_score * 0.33
        + album_score * 0.15
        + duration_score * 0.10
    )

    hard_reasons: list[str] = []
    if title_score < 0.72:
        hard_reasons.append("title mismatch")
    if artist_score < 0.34:
        hard_reasons.append("artist mismatch")
    if duration_mismatch:
        hard_reasons.append("duration mismatch")

    source_isrc = normalize_isrc(source.isrc)
    candidate_isrc = normalize_isrc(candidate.isrc)
    if source_isrc and candidate_isrc and source_isrc != candidate_isrc:
        hard_reasons.append("isrc mismatch")

    return CandidateScore(
        candidate=candidate,
        score=round(score, 6),
        title_score=round(title_score, 6),
        artist_score=round(artist_score, 6),
        album_score=round(album_score, 6),
        duration_score=round(duration_score, 6),
        hard_reasons=tuple(hard_reasons),
    )


def choose_best_match(
    source: TrackIdentity,
    candidates: list[SpotifyCandidate],
    *,
    auto_select_threshold: float = 0.92,
    review_threshold: float = 0.78,
    ambiguity_margin: float = 0.15,
) -> MatchDecision:
    usable_candidates = [
        candidate for candidate in candidates if candidate.spotify_id or candidate.uri
    ]
    if not usable_candidates:
        return MatchDecision(
            status=MatchStatus.REJECTED,
            confidence=0.0,
            method="none",
            reasons=("No Spotify candidates with an id or uri.",),
        )

    source_isrc = normalize_isrc(source.isrc)
    if source_isrc:
        for candidate in usable_candidates:
            if normalize_isrc(candidate.isrc) == source_isrc:
                return MatchDecision(
                    status=MatchStatus.SELECTED,
                    confidence=1.0,
                    method="isrc",
                    candidate=candidate,
                    reasons=("Exact ISRC match.",),
                )

    scores = tuple(
        sorted(
            (score_candidate(source, candidate) for candidate in usable_candidates),
            key=lambda item: item.score,
            reverse=True,
        )
    )
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None

    if best.hard_reasons:
        return MatchDecision(
            status=MatchStatus.REJECTED,
            confidence=best.score,
            method="scored",
            reasons=best.hard_reasons,
            scores=scores,
        )

    if best.score < review_threshold:
        return MatchDecision(
            status=MatchStatus.REJECTED,
            confidence=best.score,
            method="scored",
            reasons=("Best candidate is below review threshold.",),
            scores=scores,
        )

    if second and best.score - second.score < ambiguity_margin:
        return MatchDecision(
            status=MatchStatus.REVIEW,
            confidence=best.score,
            method="scored",
            candidate=best.candidate,
            reasons=("Ambiguous candidates; top score margin is too small.",),
            scores=scores,
        )

    if best.score >= auto_select_threshold:
        return MatchDecision(
            status=MatchStatus.SELECTED,
            confidence=best.score,
            method="scored",
            candidate=best.candidate,
            reasons=("High-confidence metadata match.",),
            scores=scores,
        )

    return MatchDecision(
        status=MatchStatus.REVIEW,
        confidence=best.score,
        method="scored",
        candidate=best.candidate,
        reasons=("Candidate needs manual review before writing to Spotify.",),
        scores=scores,
    )
