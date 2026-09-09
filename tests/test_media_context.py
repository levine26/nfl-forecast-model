from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from nfl_forecast.media_context import add_media_context, apply_source_first_reads


class _Response:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Session:
    def get(self, url, **kwargs):
        if "espn.com" in url:
            return _Response({
                "articles": [{
                    "headline": "Patriots-Seahawks rematch opens the season",
                    "description": "Seattle and New England meet again after the Super Bowl.",
                    "published": "2026-09-09T10:00:00Z",
                    "links": {"web": {"href": "https://www.espn.com/example"}},
                }]
            })
        return _Response(content=b"<rss><channel></channel></rss>")


def _predictions():
    return pd.DataFrame([{
        "game_id": "2026_01_NE_SEA",
        "season": 2026,
        "week": 1,
        "away_team": "NE",
        "home_team": "SEA",
        "pick": "SEA",
    }])


def test_curated_read_becomes_public_lead_without_changing_model_fields(tmp_path: Path):
    config = {
        "games": {
            "2026_01_NE_SEA": {
                "headline": "A rematch with a new shape",
                "read": "This is a human reporting-led paragraph about the actual game.",
                "source_name": "NFL.com",
                "source_url": "https://www.nfl.com/example",
            }
        }
    }
    (tmp_path / "media_editorial_seeds_2026_w1.json").write_text(json.dumps(config))
    evidence, status = add_media_context(
        _predictions(), {}, 2026, 1, config_dir=tmp_path, session=_Session()
    )
    assert status["games_with_curated_read"] == 1
    direct = [item for item in evidence["2026_01_NE_SEA"] if (item.get("metadata") or {}).get("direct_read")]
    assert len(direct) == 1

    previews = {
        "2026_01_NE_SEA": {
            "headline": "Old template headline",
            "paragraphs": ["Old template Read.", "Market paragraph stays."],
            "editorial_voice": {"primary_variant": 3},
            "story_spine": {},
            "final_home_prob": 0.61,
        }
    }
    result = apply_source_first_reads(previews, evidence, _predictions())
    preview = result["2026_01_NE_SEA"]
    assert preview["headline"] == "A rematch with a new shape"
    assert preview["paragraphs"][0].startswith("This is a human reporting-led")
    assert preview["paragraphs"][1] == "Market paragraph stays."
    assert preview["final_home_prob"] == 0.61
    assert preview["editorial_voice"]["source_first_reporting"] is True
    assert preview["story_spine"]["primary_family"] == "media_reporting"


def test_live_espn_reporting_is_attached_as_source_evidence_without_copying_description():
    evidence, status = add_media_context(
        _predictions(), {}, 2026, 99, config_dir="does-not-exist", session=_Session()
    )
    assert status["games_with_live_reporting"] == 1
    media = [item for item in evidence["2026_01_NE_SEA"] if (item.get("metadata") or {}).get("family") == "media_reporting"]
    assert media
    espn = next(item for item in media if item.get("source_name") == "ESPN")
    assert "Super Bowl" not in espn["summary"]
    assert espn["source_url"] == "https://www.espn.com/example"
    assert (espn.get("metadata") or {}).get("promoted_to_model") is False
