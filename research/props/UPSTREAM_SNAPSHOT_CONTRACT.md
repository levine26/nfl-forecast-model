# LevLine Props Upstream Snapshot Contract

Status: **RESEARCH BETA**  
Scope: offensive player props only  
Operator entrypoint: `scripts/build_props_upstream_snapshot.py`

## Purpose

This layer removes manual construction of the opportunity and efficiency handoff tables. It does not introduce a new predictive model.

The builder may derive only observable, strictly lagged history from nflverse play-by-play and the existing canonical current player-state contract. Every non-observable assumption remains explicit caller input.

## Observable history

`build_lagged_props_history()` uses the same `STRICT_PRIOR_WEEK` horizon as the canonical player-state lane:

- target-week PBP is excluded in full;
- prior 2026 weeks may update chronological state but may not be used for feature/model/hyperparameter/threshold selection;
- team opportunities are reconstructed as:
  - dropbacks = pass attempts + sacks + QB scrambles;
  - designed rushes = team rush attempts - QB scrambles;
  - offensive plays = dropbacks + designed rushes;
  - team targets = stable receiver-ID target events;
- QB scrambles are kept separate from designed carries;
- player target/reception and scoring-area opportunity counts use stable IDs;
- efficiency sufficient statistics are observed pass/rush/receiving counts and yards only.

The build fails closed when explicit `qb_scramble` evidence or the required yardage fields are absent. Missing historical player position identity is not guessed.

## Mandatory explicit assumptions

The priors file must contain:

```json
{
  "source_status": "qualified | prospective_unqualified | unknown",
  "prior_model_trained_through_season": 2025,
  "route_prior_means": {
    "RB": "<preregistered mean in (0,1)>",
    "WR": "<preregistered mean in (0,1)>",
    "TE": "<preregistered mean in (0,1)>"
  },
  "availability_beta_priors": {
    "UNKNOWN": {"alpha": "<positive>", "beta": "<positive>"},
    "QUESTIONABLE": {"alpha": "<positive>", "beta": "<positive>"},
    "DOUBTFUL": {"alpha": "<positive>", "beta": "<positive>"}
  },
  "efficiency_position_priors": {
    "QB": {"<all efficiency prior fields>": "<pre-2026 value>"},
    "RB": {"<all efficiency prior fields>": "<pre-2026 value>"},
    "WR": {"<all efficiency prior fields>": "<pre-2026 value>"},
    "TE": {"<all efficiency prior fields>": "<pre-2026 value>"}
  }
}
```

No values are supplied by this contract. A prior claiming training through 2026 is rejected.

The scoring-context file must provide, per target game and team:

- `expected_drives`
- `expected_red_zone_trips`
- `prior_red_zone_td_rate`
- `prior_pass_td_fraction`
- `expected_non_red_zone_pass_tds`
- `expected_non_red_zone_rush_tds`
- explicit residual-bucket efficiency for both teams

These are upstream model inputs, not sportsbook-derived values.

If the canonical lagged role cannot uniquely identify the current starting QB, `primary_qb_by_team` must contain a stable player ID and explicit point-in-time provenance. The builder does not guess a starter from depth-chart order or actual game participation.

## Operator flow

For one game:

```bash
python scripts/build_props_upstream_snapshot.py \
  --season 2026 \
  --week 3 \
  --game-id <canonical_game_id> \
  --priors /secure/path/preregistered_props_priors.json \
  --scoring-context /secure/path/pregame_scoring_context.json \
  --output-dir /secure/path/props_upstream/<canonical_game_id>
```

The script:

1. loads nflverse schedule/PBP/snap/current-roster sources through the existing Props source adapter;
2. loads the nflverse stable player identity table;
3. attempts to capture the current NFL injury report unless `--skip-injury-fetch` is specified;
4. timestamps the forecast only after live source requests complete;
5. builds canonical current player state;
6. derives strictly lagged opportunity and efficiency history;
7. executes the actual opportunity and efficiency/TD lane interfaces;
8. writes immutable create-only artifacts.

Output files include:

- `player_state.json` — full target-week canonical state for stable-ID sportsbook resolution;
- `<game>.opportunity.json`;
- `<game>.efficiency_player.json`;
- `<game>.team_td.json`;
- `<game>.residual_efficiency.json`;
- `<game>.game_spec.json`;
- `<game>.upstream_audit.json`.

If injury fetching is unavailable, the builder does not silently mark unlisted players healthy. Availability remains `UNKNOWN` and therefore requires the explicit configured Beta prior.

## Final freeze ordering

The upstream snapshot is intentionally created before the sportsbook capture. The final integration manifest must therefore receive a freeze timestamp **after** the market snapshot exists.

`scripts/build_props_integration_manifest.py` uses the game-spec timestamp when one is explicitly supplied; otherwise it stamps current UTC at manifest assembly. `--forecast-timestamp` can supply an explicit timezone-aware final freeze time.

The manifest assembler still requires every component timestamp to be no later than that final forecast time and strictly before kickoff.

## Governance

This layer:

- is research-only;
- never imports sportsbook prices into opportunity/efficiency modeling;
- never mutates official LevLine/F-ST winner probabilities;
- never uses target-week or current-game PBP;
- never supplies route, availability, efficiency, scoring or residual-efficiency defaults;
- never treats missing current availability as `AVAILABLE`;
- refuses priors trained through completed 2026 outcomes.
