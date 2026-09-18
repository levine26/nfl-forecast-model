# LevLine Props 2.0 Challenger Research Preregistration

Status: **RESEARCH-ONLY / NOT PRODUCTION AUTHORIZED**  
Created: 2026-09-18  
Baseline: `levline-props-historical-directional-v1.0`  
Frozen V1 historical accuracy: **51.02% (2,888 / 5,660 decided non-push props)**  
Branch: `research/props-v2-challenger`

## Objective

Develop challengers that can improve LevLine Props forecasting without modifying the official
LevLine/F-ST winner model and without post-hoc relabeling of historical evidence.

The V1 historical result is a frozen benchmark, not a tuning target to be cosmetically improved.

## Evidence boundary

The 2023-2025 V1 historical ledger has already been inspected for aggregate diagnostics and is
therefore **research-development evidence**, not a pristine final promotion holdout for Props 2.0.
Any retrospective Props 2.0 result from these seasons must be labeled accordingly.

Completed 2026 outcomes remain prohibited from architecture, feature, hyperparameter, calibration,
threshold, or weighting selection. 2026 forecasts may be recorded prospectively and graded later
as untouched shadow evidence.

No selective MODEL EDGE threshold may be chosen from 2023-2025 outcomes and then described as
prospective evidence.

## Frozen problems to attack

1. V1 Fair-Line MAE (19.18) was worse than the sportsbook OPEN line (15.93).
2. The magnitude of V1 line disagreement did not establish monotonic realized accuracy.
3. V1 historical reconstruction used fixed receiving route priors in the absence of route evidence.
4. Matchup adjustment architecture existed but remained neutral without validated coefficients.
5. Availability was primarily an active/inactive probability rather than a conditional workload
   mixture.
6. Yardage simulation used intentionally simple compound distributions that may miss negative plays
   and play-type mixtures.

## Challenger program

### C1 — Market-as-prior residual calibration

Question: **Does LevLine contain incremental information after the sportsbook market is treated as
the prior?**

For two-way line markets, compute the sportsbook no-vig probability and combine it with the frozen
LevLine probability through a constrained residual model:

```
logit(P_over_challenger)
    = logit(P_over_market)
    + intercept
    + beta * [logit(P_over_levline) - logit(P_over_market)]
```

This is deliberately low-dimensional. The market coefficient is fixed at 1.0; LevLine may only add
a residual correction. The residual coefficient receives L2 shrinkage toward zero.

The first implementation is an evaluation/research layer only. It does not mutate the underlying
football simulation, Fair Line, or V1 receipts.

Primary comparison:
- all-call directional accuracy versus frozen V1;
- all-call directional accuracy versus market-price favorite direction;
- Brier score and log loss;
- game-clustered paired accuracy difference.

No abstention threshold is used for the primary comparison.

### C2 — Dynamic role state

Replace static receiving-route priors with strictly lagged player role state when source-qualified
participation evidence is available. Candidate latent states include:
- offensive snap participation;
- route participation;
- target share / targets per route;
- carry share;
- red-zone and goal-line opportunity share.

The state must be estimated only from games completed before the forecast timestamp. Missing live
route data must fail back to preregistered priors rather than inferred postgame participation.

Historical nflverse participation data may be used only where it was genuinely available for
retrospective reconstruction. It must never be mistaken for a live in-season source.

### C3 — Decomposed efficiency

Research challenger decomposition:
- passing: dropbacks -> attempts -> completions -> air yards/YAC;
- receiving: routes -> targets -> completions -> air yards/YAC;
- rushing: carries -> contextual expected yards -> player residual efficiency.

Any advanced-stat prior must be fit on seasons strictly before the evaluated target season in
historical reconstruction.

### C4 — Matchup coefficients

Candidate matchup fields already admitted by the frozen schema may be activated only after a
separate rolling-origin fit:
- pressure/pass-rush and OL mismatch;
- man/zone/coverage-shell interaction;
- slot/outside/RB-linebacker coverage;
- YAC/tackling suppression;
- box/run-defense interaction;
- red-zone defense;
- QB scramble-pressure interaction;
- defensive availability.

Coefficients trained on completed 2026 outcomes are prohibited.

### C5 — Availability/workload mixtures

Research OUT / ACTIVE-LIMITED / ACTIVE-NORMAL workload mixtures rather than reducing uncertainty to
a binary active probability. The mixture must be generated from pregame evidence and historical
priors only.

### C6 — Distribution challenger

Test empirically justified event-level distributions and mixture models. Negative rushing/receiving
plays must be representable where the underlying process allows them. Distributional promotion
requires improved proper scoring/calibration, not visually nicer tails.

## Retrospective development protocol

The existing 2023-2025 ledger is permitted for research development, but all results must carry the
label **RETROSPECTIVE CHALLENGER DEVELOPMENT — NOT PROMOTION EVIDENCE**.

For C1:
- fit/calibrate only from rows chronologically before the evaluated block;
- preserve exact market prices and model probabilities from the original frozen receipts;
- exclude pushes from directional accuracy;
- do not create synthetic prices;
- report market-only and frozen-V1 baselines side-by-side;
- cluster uncertainty by game.

Because prior analysis has already inspected 2023-2025 aggregate outcomes, a positive retrospective
result cannot itself authorize production.

## Promotion gates

No Props 2.0 challenger may replace V1 unless it earns promotion on untouched prospective evidence.

Minimum requirements:
1. reproducible immutable forecast receipts;
2. no completed-2026 tuning;
3. directional accuracy improvement over V1 with uncertainty reported;
4. calibration/Brier/log-loss no worse and preferably better;
5. Fair-Line/projection error improved where the challenger produces a Fair Line;
6. claimed edge magnitude is monotonic with realized accuracy/calibration;
7. no evidence that gains come only from one tiny subgroup;
8. market-relative comparison and CLV reported when source-qualified closing data exist;
9. research firewall and official winner model remain unchanged.

A selective betting signal is a separate future experiment and must have its own preregistered
threshold-development and untouched validation sample.

## Scientific interpretation

Failure is an acceptable result. If the market-only baseline remains superior to every football
residual challenger, LevLine Props should use that evidence to redesign the football inputs rather
than invent a betting threshold.

