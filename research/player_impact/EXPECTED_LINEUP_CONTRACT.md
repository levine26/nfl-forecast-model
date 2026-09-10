# LevLine Player Impact Engine — Expected Lineup Contract

Status: **research / explainability only**. This contract does not authorize any player-derived feature in `final_home_prob`.

## Purpose

The expected-lineup layer estimates modeled lineup value lost/gained, replacement burden, unit state, uncertainty, and matchup context from information explicitly available before the game. It is designed for internal research, game-card intelligence, injury/availability summaries, lineup-change diagnostics, market-disagreement analysis, and eventual Sunday Signal explanatory context.

It is not a continuation or rescue of `V09A-PLAYER-VALUE-001`. V09A's direct target/rush player-value probability formulation remains rejected. This layer uses a different objective: represent expected lineup state and football intelligence first, then test incremental probability value only through a separately pre-registered future experiment.

## Required player-row inputs

Each row must identify `game_id`, `season`, `week`, `team`, a stable `player_id`, `player_name`, `unit`, and `role`. The six registered units are `qb`, `skill`, `ol`, `pass_rush`, `run_defense`, and `secondary`.

Modeled inputs are explicit: `modeled_player_value`, `replacement_value`, `expected_role_share`, `availability_probability`, `value_uncertainty`, `availability_uncertainty`, `feature_data_horizon`, and `availability_source_status`.

`availability_source_status` must be one of:

- `qualified`: source has passed the relevant timestamp/identity qualification for the intended use;
- `prospective_unqualified`: genuinely pregame prospective information, but not historically qualified for a 2022–2025 validation claim;
- `unknown`: no defensible availability source qualification is available. The engine preserves this uncertainty rather than inventing certainty.

The engine does not infer missing availability or replacement values.

## Hard leakage guard

Input fails closed if it contains fields representing actual current-game snaps, actual participation, postgame player value, final inactive status learned after kickoff, game outcome, or final scores. Actual snaps are never used as a retrospective proxy for pregame availability.

Stable IDs are mandatory. Ambiguous/fuzzy identity is not silently resolved at this layer.

## Modeled outputs

Player rows expose value over replacement, expected available role share, expected value over replacement, expected lineup value lost, expected lineup value gained, replacement burden, and modeled uncertainty.

Unit rows aggregate the same concepts for QB, skill, OL, pass rush, run defense, and secondary, plus replacement quality, expected availability, uncertainty, and counts of qualified versus unqualified/unknown availability rows.

Team rows expose total lineup value lost/gained, replacement burden, lineup uncertainty, and separate QB/skill/OL/pass-rush/run-defense/secondary modeled impacts.

Game context compares opposing unit states to produce signed pass-protection, receiving, and run-matchup risk diagnostics. These are LevLine research-scale diagnostics, not official NFL statistics and not direct win-probability deltas.

## Probability firewall

Every modeled output is stamped `research_only=True` and `probability_feature_authorized=False`. The public site and production pipeline do not consume these outputs.

A future player-probability experiment must receive a new candidate ID and ask the pre-registered question: whether leakage-safe expected lineup impact adds incremental probability-quality signal beyond frozen F-ST. Failure of that future experiment leaves this engine useful for explainability; it does not justify feature fishing or post-hoc rescue tuning.
