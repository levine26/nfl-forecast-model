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

The minimal priors file now contains only assumptions that the repository cannot derive from a trustworthy live/point-in-time source:

```json
{
  "route_prior_means": {
    "RB": "<preregistered mean in (0,1)>",
    "WR": "<preregistered mean in (0,1)>",
    "TE": "<preregistered mean in (0,1)>"
  },
  "availability_beta_priors": {
    "UNKNOWN": {"alpha": "<positive>", "beta": "<positive>"}
  }
}
```

Those values are deliberately not invented by this contract.

`QUESTIONABLE` and `DOUBTFUL` priors are fit automatically when historical sources are available. The fit joins official historical injury-report designations to PFR offensive snap counts for the overlapping 2012–2024 regular seasons, uses a fixed structural Beta(1,1) prior, and treats a missing player snap row as zero only when that team-week is present in the snap source. The historical nflverse injury pipeline currently ends after 2024, so this fit is necessarily pre-2026. Explicit configured Q/D priors may override the empirical fit. If the historical source is unavailable, the operator falls back to explicit configuration and otherwise fails closed when a Q/D player needs a prior.

`UNKNOWN` remains explicit because it includes absence of a trustworthy current availability source. That state is not statistically equivalent to a player being listed as Questionable or Doubtful, so the builder does not infer an UNKNOWN probability from historical injury-report omissions.

By default, conditional-efficiency priors are fit empirically from regular-season PBP ending in 2025. Completed 2026 outcomes are structurally excluded from this prior fit. The fitter produces position priors for completion rate, yards/completion, rushing YPC, catch rate, receiving YPR, red-zone/end-zone target rate and goal-line carry rate, plus residual-bucket efficiency.

By default, team scoring context is also derived rather than hand-entered:

- expected drives and red-zone trips use strictly lagged team history, so prior completed 2026 games may update current state;
- expected non-red-zone passing/rushing TD volume uses the same strictly lagged team state;
- red-zone TD conversion and pass-vs-rush TD fraction are frozen to league regular-season evidence ending in 2025.

An optional scoring-context file may override these quantities for a controlled preregistered experiment. Explicit efficiency priors may likewise be supplied in the priors file, but then `prior_model_trained_through_season` is mandatory and values trained through 2026 are rejected.

For current QB identity, the operator first consumes timestamped 2025+ nflverse depth charts at or before the forecast timestamp. A unique rank-1 QB with a stable GSIS ID is accepted with snapshot provenance. Ambiguous/future/missing depth-chart evidence fails closed. An explicit `primary_qb_by_team` entry with point-in-time provenance may override the depth-chart resolution when needed.

## Operator flow

For the complete target week:

```bash
python scripts/build_props_upstream_snapshot.py \
  --season 2026 \
  --week 3 \
  --all-games \
  --priors /secure/path/preregistered_props_priors.json \
  --output-dir /secure/path/props_upstream
```

A restricted research subset can instead pass one or more explicit game IDs:

```bash
python scripts/build_props_upstream_snapshot.py \
  --season 2026 \
  --week 3 \
  --game-id <game_id_1> <game_id_2> \
  --priors /secure/path/preregistered_props_priors.json \
  --output-dir /secure/path/props_upstream
```

The script loads/fits weekly shared inputs once, builds every selected game in memory, and writes nothing until all games validate and all output destinations pass create-only preflight.

The script:

1. loads nflverse schedule/PBP/snap/current-roster sources through the existing Props source adapter;
2. loads the nflverse stable player identity table;
3. attempts to capture the current NFL injury report unless `--skip-injury-fetch` is specified;
4. timestamps the forecast only after live source requests complete;
5. builds canonical current player state and resolves QB1 from the latest eligible timestamped depth chart when possible;
6. derives strictly lagged opportunity/efficiency history;
7. fits efficiency priors only through 2025 and derives current scoring-volume state from strictly prior weeks unless explicit preregistered overrides are supplied;
8. executes the actual opportunity and efficiency/TD lane interfaces;
9. writes immutable create-only artifacts.

Output files include:

- `player_state.json` — one full target-week canonical state for stable-ID sportsbook resolution;
- `upstream_slate.json` — immutable index of every selected game and its component paths;
- for multi-game builds, `games/<game_id>/` containing:
  - `<game>.opportunity.json`;
  - `<game>.efficiency_player.json`;
  - `<game>.team_td.json`;
  - `<game>.residual_efficiency.json`;
  - `<game>.game_spec.json`;
  - `<game>.upstream_audit.json`.

Single-game mode preserves the component files directly under the requested output directory while still emitting `upstream_slate.json`.

If injury fetching is unavailable, the builder does not silently mark unlisted players healthy. Availability remains `UNKNOWN` and therefore requires the explicit configured Beta prior.

## Final freeze ordering

The upstream slate is intentionally created before the sportsbook capture. The final integration manifests therefore receive one common freeze timestamp **after** the market snapshot exists.

In slate mode, `scripts/build_props_integration_manifest.py` consumes `upstream_slate.json`, fingerprints the entire upstream index and sportsbook snapshot, applies one current-UTC final freeze time to every selected game unless an explicit timezone-aware `--forecast-timestamp` is supplied, and emits `manifest_slate.json`.

The manifest assembler still requires every component timestamp to be no later than that final forecast time and strictly before each game's kickoff. If any selected game violates that ordering, the slate assembly fails before writing any manifest file.

## Governance

This layer:

- is research-only;
- never imports sportsbook prices into opportunity/efficiency modeling;
- never mutates official LevLine/F-ST winner probabilities;
- never uses target-week or current-game PBP;
- never supplies a hidden route or UNKNOWN-availability default;
- fits Q/D availability only from historical injury designations and offensive snaps ending in 2024, with explicit source-coverage checks;
- fits default efficiency/residual priors only from regular-season data through 2025;
- allows prior completed 2026 games only to update chronological team state, never prior fitting/tuning;
- never treats missing current availability as `AVAILABLE`;
- refuses priors trained through completed 2026 outcomes.
