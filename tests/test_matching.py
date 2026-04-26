import unittest

from music_likes_sync.matching import (
    MatchStatus,
    SpotifyCandidate,
    TrackIdentity,
    choose_best_match,
)


class MatchingDecisionTests(unittest.TestCase):
    def test_featured_artist_can_move_between_title_and_artist_fields(self):
        source = TrackIdentity(
            title="Wicked Games (feat. Anna Naklab)",
            artists=["Parra for Cuva"],
            album="Wicked Games",
            duration_seconds=195,
        )
        candidate = SpotifyCandidate(
            title="Wicked Games",
            artists=["Parra for Cuva", "Anna Naklab"],
            album="Wicked Games",
            duration_ms=196_000,
            spotify_id="spotify-good",
        )

        decision = choose_best_match(source, [candidate])

        self.assertEqual(decision.status, MatchStatus.SELECTED)
        self.assertEqual(decision.candidate.spotify_id, "spotify-good")
        self.assertGreaterEqual(decision.confidence, 0.92)

    def test_rejects_search_hit_with_wrong_artist_even_when_title_matches(self):
        source = TrackIdentity(
            title="Survival",
            artists=["Yes"],
            album="The Yes Album",
            duration_seconds=258,
        )
        candidate = SpotifyCandidate(
            title="Survival",
            artists=["Muse"],
            album="Survival",
            duration_ms=257_000,
            spotify_id="wrong-artist",
        )

        decision = choose_best_match(source, [candidate])

        self.assertEqual(decision.status, MatchStatus.REJECTED)
        self.assertIsNone(decision.candidate)
        self.assertIn("artist", " ".join(decision.reasons).lower())

    def test_rejects_duration_mismatch_when_metadata_available(self):
        source = TrackIdentity(
            title="Everything In Its Right Place",
            artists=["Radiohead"],
            album="Kid A",
            duration_seconds=251,
        )
        candidate = SpotifyCandidate(
            title="Everything In Its Right Place",
            artists=["Radiohead"],
            album="Kid A",
            duration_ms=420_000,
            spotify_id="wrong-version",
        )

        decision = choose_best_match(source, [candidate])

        self.assertEqual(decision.status, MatchStatus.REJECTED)
        self.assertIsNone(decision.candidate)
        self.assertIn("duration", " ".join(decision.reasons).lower())

    def test_requires_review_when_top_candidates_are_too_close(self):
        source = TrackIdentity(
            title="Halo",
            artists=["Beyonce"],
            album="I Am... Sasha Fierce",
            duration_seconds=261,
        )
        studio = SpotifyCandidate(
            title="Halo",
            artists=["Beyonce"],
            album="I Am... Sasha Fierce",
            duration_ms=261_000,
            spotify_id="studio",
        )
        alternate = SpotifyCandidate(
            title="Halo",
            artists=["Beyonce"],
            album="Halo",
            duration_ms=260_000,
            spotify_id="alternate-release",
        )

        decision = choose_best_match(source, [studio, alternate])

        self.assertEqual(decision.status, MatchStatus.REVIEW)
        self.assertEqual(decision.candidate.spotify_id, "studio")
        self.assertIn("ambiguous", " ".join(decision.reasons).lower())

    def test_isrc_exact_match_selects_despite_text_variation(self):
        source = TrackIdentity(
            title="Different local title",
            artists=["Different local artist"],
            album="Different local album",
            duration_seconds=0,
            isrc="USRC17607839",
        )
        candidate = SpotifyCandidate(
            title="Canonical Title",
            artists=["Canonical Artist"],
            album="Canonical Album",
            duration_ms=0,
            isrc="usrc17607839",
            spotify_id="isrc-match",
        )

        decision = choose_best_match(source, [candidate])

        self.assertEqual(decision.status, MatchStatus.SELECTED)
        self.assertEqual(decision.method, "isrc")
        self.assertEqual(decision.confidence, 1.0)
        self.assertEqual(decision.candidate.spotify_id, "isrc-match")


if __name__ == "__main__":
    unittest.main()
