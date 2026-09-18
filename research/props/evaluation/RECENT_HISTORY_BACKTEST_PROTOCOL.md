# LevLine Props Recent-History Backtest Protocol

Frozen before historical outcome inspection for the 2023-2025 replay.

## Objective

Estimate the simple headline side accuracy for LevLine Props in the same human-readable form as LevLine winner accuracy:

> correct non-push prop sides / graded non-push prop sides

This is a research-only historical reconstruction of the current Props architecture. It must not alter the official LevLine/F-ST winner model and must not tune model architecture or thresholds from these outcomes.

## Evaluation seasons

Primary window: 2023, 2024, 2025 NFL seasons.

The source audit established broad historical player-prop coverage in all three seasons. No earlier season is needed for headline grading, although earlier nflverse PBP may be used only as lagged training/history input.

## Historical sportsbook source

Source repository: `gcampb41/nfl_data-` (documented upstream: `theedgepredictor/odds-data-pump`), Action Network player-prop data.

Headline threshold policy:

1. use `book_id == 30` (OPEN);
2. require `open_inferred == false`;
3. require supported player identity and supported offensive position;
4. require a two-way total market with both Over and Under at the same threshold;
5. never use `last_updated` as proof of historical capture time because the archival dataset was retrieved later;
6. treat Action Network's provider-designated OPEN field as the historical opening threshold;
7. do not use consensus/DK/FD/bet365 fallbacks in the headline. Those may appear only as labeled sensitivity analyses.

Supported headline line markets:

- passing_yards
- rushing_yards
- receiving_yards
- receptions
- passing_tds

Rushing/receiving/anytime TD binary markets are evaluated separately when defensible because the archived dataset often contains one-sided YES prices rather than a complete two-way side market.

## Point-in-time replay

For a target season S and week W:

- all opportunity/player efficiency state must come from seasons/weeks strictly earlier than (S, W);
- league efficiency priors are fit only through season S-1;
- team scoring-state priors are fit only through S-1, with team state restricted to prior games;
- no target-game or later outcome may enter model construction;
- current modeled player eligibility comes from players with a historical pregame market listing, not from final box-score participation;
- a primary QB may be identified only when exactly one team QB has a passing-yards market listing. Ambiguous QB situations fail closed;
- no sportsbook threshold or price is passed into the football simulation.

Historical route observations are unavailable in the current default pipeline. The replay therefore uses the already-existing integration-test explicit position route priors, frozen before grading:

- RB: 0.55
- WR: 0.90
- TE: 0.75

These values are not selected from 2023-2025 outcomes.

Market-listed players are modeled as available for the replay. Postgame participation is used only for grading/void logic, never as a forecast input.

## Grading

A historical prop is gradeable only if:

- the player has a valid stable GSIS ID;
- the game/event maps uniquely to the nflverse schedule;
- the player participated according to qualified postgame participation evidence (snap-count evidence preferred);
- an actual statistic can be reconstructed from nflverse PBP;
- the prop threshold is a qualified real OPEN line.

For each gradeable line market:

- model Over if simulated P(Over) > simulated P(Under);
- model Under if simulated P(Under) > simulated P(Over);
- ties are no-picks and excluded;
- actual > line = Over win;
- actual < line = Under win;
- actual == line = push and excluded from headline accuracy.

No confidence/edge threshold is introduced for the headline. Accuracy is measured across every qualified model side.

## Simulation

Use the frozen integrated Props architecture. Monte Carlo randomness is deterministic by game/season seed. The same simulation count is used across the headline sample. A convergence sensitivity may rerun a subset at a larger simulation count but may not alter the historical model.

## Required reporting

At minimum report:

- overall correct / incorrect / pushes / no-picks / accuracy;
- N games, players, props;
- accuracy by season;
- accuracy by prop family;
- accuracy by position;
- game-clustered 95% confidence interval;
- model mean/Fair-Line MAE where available;
- sportsbook threshold baseline diagnostics;
- explicit source/reconstruction limitations.

No result may be described as prospective evidence. It is historical out-of-sample reconstruction under this protocol.
