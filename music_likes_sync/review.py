"""Offline dry-run review helpers for cached Spotify search results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from music_likes_sync.legacy import decide_legacy_item


def review_search_results(search_results: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [decide_legacy_item(item) for item in search_results]
    summary = {
        "total": len(matches),
        "selected": 0,
        "review": 0,
        "rejected": 0,
    }
    for match in matches:
        status = match.get("status", "rejected")
        summary[status] = summary.get(status, 0) + 1
    return {
        "summary": summary,
        "matches": matches,
    }


def write_review(input_path: Path, output_path: Path) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8") as file:
        search_results = json.load(file)
    review = review_search_results(search_results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(review, file, ensure_ascii=False, indent=2)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description="Review cached MusicLikesSync match candidates without writing to Spotify.")
    parser.add_argument(
        "input",
        nargs="?",
        default="data/search_results.json",
        help="Path to cached search_results.json",
    )
    parser.add_argument(
        "--output",
        default="data/dry_run_match_review.json",
        help="Path to write the dry-run review JSON",
    )
    args = parser.parse_args()

    review = write_review(Path(args.input), Path(args.output))
    summary = review["summary"]
    print(
        "Dry-run review: "
        f"{summary['total']} total, "
        f"{summary.get('selected', 0)} selected, "
        f"{summary.get('review', 0)} review, "
        f"{summary.get('rejected', 0)} rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
