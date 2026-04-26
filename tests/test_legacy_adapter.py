import unittest

from music_likes_sync.legacy import decide_legacy_item


class LegacyAdapterTests(unittest.TestCase):
    def test_ignores_empty_placeholder_variants(self):
        item = {
            "title": "Wicked Games (feat. Anna Naklab)",
            "artist": "Parra for Cuva",
            "album": "Wicked Games",
            "variants": [
                {
                    "spotify_title": "",
                    "spotify_artist": "",
                    "spotify_album": "",
                    "spotify_id": "",
                },
                {
                    "spotify_title": "Wicked Games",
                    "spotify_artist": "Parra for Cuva, Anna Naklab",
                    "spotify_album": "Wicked Games",
                    "spotify_id": "spotify-good",
                    "spotify_duration_ms": 196000,
                },
            ],
        }

        result = decide_legacy_item(item)

        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["best_variant"]["spotify_id"], "spotify-good")
        self.assertGreaterEqual(result["confidence"], 0.92)

    def test_review_status_is_preserved_for_ambiguous_candidates(self):
        item = {
            "title": "Halo",
            "artist": "Beyonce",
            "album": "I Am... Sasha Fierce",
            "duration_seconds": 261,
            "variants": [
                {
                    "spotify_title": "Halo",
                    "spotify_artist": "Beyonce",
                    "spotify_album": "I Am... Sasha Fierce",
                    "spotify_id": "studio",
                    "spotify_duration_ms": 261000,
                },
                {
                    "spotify_title": "Halo",
                    "spotify_artist": "Beyonce",
                    "spotify_album": "Halo",
                    "spotify_id": "alternate-release",
                    "spotify_duration_ms": 260000,
                },
            ],
        }

        result = decide_legacy_item(item)

        self.assertEqual(result["status"], "review")
        self.assertEqual(result["best_variant"]["spotify_id"], "studio")
        self.assertIn("Ambiguous", result["reason"])


if __name__ == "__main__":
    unittest.main()
