from __future__ import annotations

import argparse
import json
from pathlib import Path

from nfl_forecast.player_impact_cards import build_payload


def example_card() -> dict:
    """Schema fixture only; it is not a forecast for a real player or game."""
    return {
        "schema_version": 1,
        "research_only": True,
        "example_only": True,
        "game_id": "EXAMPLE_GAME",
        "team": "EXAMPLE",
        "player_id": "example-player-001",
        "player_name": "Example Player",
        "position": "WR",
        "observed_statistics": [
            {
                "kind": "source_observed",
                "metric": "target_share",
                "value": 0.24,
                "unit": "share",
                "source_name": "nflverse play-by-play example",
                "source_url": "https://github.com/nflverse/nflverse-data/releases/tag/pbp",
                "source_data_as_of": "historical completed games only",
                "sample_size": 100,
                "redistribution_review_status": "pending"
            }
        ],
        "levline_impacts": [
            {
                "kind": "levline_modeled_impact",
                "metric": "levline_player_impact",
                "estimate": 0.0,
                "uncertainty": 1.0,
                "model_version": "schema-example-not-a-model",
                "feature_data_horizon": "example only",
                "interpretation": "Example of a LevLine modeled estimate with uncertainty; not an observed league statistic and not a player projection."
            }
        ],
        "data_quality": {
            "identity_confidence": "stable_id",
            "coverage_status": "example_only",
            "missing_fields": []
        }
    }


def run(output_dir: str = "research_outputs/player_cards") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = build_payload([example_card()], generated_utc="EXAMPLE_ONLY")
    payload["example_only"] = True
    payload["data_reliability_status"] = "schema_validation_only"
    payload["licensing_review_status"] = "pending_source_specific_review"
    path = out / "player_impact_cards.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/player_cards")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
