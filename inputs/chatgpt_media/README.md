# ChatGPT free editorial ingestion

This directory is the zero-API-cost handoff boundary for Sunday Signal editorial research.
It does **not** accept forecast inputs, probabilities, picks, locks, grading data, market data,
or model artifacts. The frozen forecast path remains `F-ST-01-FROZEN-2026`.

A production bundle lives at `inputs/chatgpt_media/current/` and contains:

1. `manifest.json`
2. exactly one `<game_id>.json` or `<game_id>.txt` file for every game in the canonical slate

Each game file must use the same focused JSON contract as the media writer:

```json
{
  "games": {
    "GAME_ID": {
      "headline": "matchup-specific headline",
      "paragraph1": "55-100 words discussing both teams and the football mechanism that decides the game",
      "model_rationale": "18-40 words of non-numerical football context supporting the selected side",
      "sources": [
        {"name": "publisher", "title": "direct report title", "url": "https://approved.publisher/direct-report"},
        {"name": "second publisher", "title": "direct report title", "url": "https://second.approved.publisher/direct-report"}
      ]
    }
  }
}
```

The manifest is intentionally strict:

```json
{
  "schema_version": 1,
  "producer": "chatgpt-consumer-session",
  "research_mode": "live-web-search",
  "forecast_path_identity": "F-ST-01-FROZEN-2026",
  "generated_utc": "2026-09-12T04:00:00Z",
  "game_ids": ["GAME_ID_1", "GAME_ID_2"]
}
```

`game_ids` must exactly match the canonical slate and order, and the manifest must be no
more than four hours old. The ingestion script stages the games one at a time through
`validate_single_copilot_game.py`, then reuses the existing merge, composition, LevLine
paragraph rendering, and full-slate publication validators. Two independent approved
direct-report publisher families, freshness, prose/rationale limits, substantive
seven-word uniqueness, headline uniqueness, and the full-slate gate remain mandatory.

The GitHub workflow validates mechanism-only pull requests without requiring a bundle.
When a complete `current/` bundle is included, pull-request CI validates the full slate;
a merge to `main` publishes only after latest-main reconciliation and the existing final
editorial launch gate. No OpenAI API key or paid model API is required: ChatGPT can do the
live research in the user session and hand the structured payloads into this directory.
