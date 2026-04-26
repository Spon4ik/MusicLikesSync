import unittest

from music_likes_sync.review import review_search_results


class ReviewTests(unittest.TestCase):
    def test_review_search_results_counts_statuses(self):
        search_results = [
            {
                "title": "Wicked Games (feat. Anna Naklab)",
                "artist": "Parra for Cuva",
                "album": "Wicked Games",
                "duration_seconds": 195,
                "variants": [
                    {
                        "spotify_title": "Wicked Games",
                        "spotify_artist": "Parra for Cuva, Anna Naklab",
                        "spotify_album": "Wicked Games",
                        "spotify_id": "spotify-good",
                        "spotify_duration_ms": 196000,
                    }
                ],
            },
            {
                "title": "Survival",
                "artist": "Yes",
                "album": "The Yes Album",
                "duration_seconds": 258,
                "variants": [
                    {
                        "spotify_title": "Survival",
                        "spotify_artist": "Muse",
                        "spotify_album": "Survival",
                        "spotify_id": "wrong-artist",
                        "spotify_duration_ms": 257000,
                    }
                ],
            },
        ]

        review = review_search_results(search_results)

        self.assertEqual(review["summary"]["total"], 2)
        self.assertEqual(review["summary"]["selected"], 1)
        self.assertEqual(review["summary"]["rejected"], 1)
        self.assertEqual(review["matches"][0]["status"], "selected")
        self.assertEqual(review["matches"][1]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
