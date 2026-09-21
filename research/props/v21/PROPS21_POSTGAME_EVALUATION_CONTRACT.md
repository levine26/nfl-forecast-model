# Props 2.1 prospective postgame evaluation contract

Status: **POST-OUTCOME IMPLEMENTATION OF PRE-OUTCOME METHODS — NOT A NEW TUNING CONTRACT**  
Version: `levline-props-2.1-postgame-eval-v0.1.0`

## Scientific boundary

This evaluator is implemented after the Week 2 Sunday games, so it does **not** claim that every implementation detail below was newly preregistered before outcomes. Its headline metric families and governance are inherited without outcome-driven selection from two contracts that were frozen before this cohort's outcomes:

1. `research/props/evaluation/PROPS_ACCURACY_EVALUATION_PREREGISTRATION.md` on branch `research/props-accuracy-evaluation`, contract `levline-props-eval-v1.0`, frozen September 17, 2026.
2. The frozen Shadow A/B grading contracts on main, including immutable-receipt validation, finalized-game checks, offensive-snap voiding, push handling, Brier/log-loss definitions, reliability reporting, and game-clustered uncertainty.

No result from this evaluator may rewrite a prospective forecast, change Props 2.1, alter V1/Market Anchor/Shadow A/Shadow B, or modify F-ST.

## Frozen cohort

Primary cohort:

- source live workflow: `35477049179`
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- Props 2.1 receipt path: `challenger_outputs/props21/forecast_originals.jsonl`
- expected Git blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- expected receipts: 3,439
- expected games: 15
- challenger version: `levline-props-2.1-sunday-v0.1`
- receipt version: `levline-props-2.1-prospective-receipt-v0.1`

The workflow must fetch this exact historical blob. Current/live Props outputs are not substitutes.

## Receipt integrity and chronology

Every admitted receipt must:

- be marked immutable;
- have `production_authorized=false`;
- have `outcome=null` at capture;
- have a unique receipt/forecast ID;
- identify the expected receipt and challenger versions;
- satisfy:
  `source_data_horizon <= source_v1_forecast <= props21_forecast < kickoff`;
- contain no future market capture relative to the Props 2.1 forecast;
- retain a valid 64-character source market SHA-256.

The historical Git blob pin is the cohort-level integrity anchor because the Props 2.1 receipt schema does not contain a per-row receipt hash.

## Outcomes and voids

Only finalized games are scored.

Outcome construction follows the frozen Shadow grading approach:

- use reproducible nflverse schedule/PBP sources;
- normalize nflverse QB scramble semantics;
- require the target game to be complete in the PBP source;
- resolve canonical snap-count player identity;
- require offense snaps > 0;
- zero offensive snaps are void;
- missing participation stays ungraded;
- positive-snap players with no qualifying event receive zero for that statistic.

Supported realized statistics:

- passing yards;
- rushing yards;
- receiving yards;
- receptions;
- passing TDs;
- rushing TDs;
- receiving TDs;
- anytime TD, defined consistently with the LevLine offensive model as rushing + receiving TDs (not passing TDs or return TDs).

A game that has not yet kicked off or is not finalized remains ungraded. It is never scored as zero.

## Point forecast metrics

For line/count markets where a point forecast is semantically valid:

- model-mean MAE;
- model-mean RMSE;
- median absolute error;
- signed error / bias;
- Fair-Line MAE using the frozen Props 2.1 model median;
- market-line MAE on identical matched observations;
- paired Fair-Line-minus-market absolute-error difference.

Primary point metrics are reported by prop family because pooling yards, receptions, and TD counts creates unit-mixed quantities.

Additional descriptive slices may be reported by position, model-volume bucket, market-liquidity bucket, and frozen availability/role state. These slices are descriptive diagnostics, not newly preregistered promotion criteria.

## Probability metrics

For non-push Over/Under outcomes and binary TD events:

- Brier score;
- log loss with numerical clipping only at 1e-12;
- calibration-in-the-large / mean calibration error;
- reliability bins;
- sharpness;
- calibration slope/intercept when sample support permits.

Market probability comparisons use only the identical player/prop/threshold rows where a genuine frozen no-vig market probability exists.

Pushes remain in point-error reporting but are excluded from binary Brier/log-loss.

## Distribution metrics

Props 2.1 receipts preserve point summaries and threshold probabilities but do not preserve a lossless full predictive distribution.

Therefore:

- CRPS is **not available from the Props 2.1 receipt alone**;
- PIT/rank diagnostics are **not available from the Props 2.1 receipt alone**;
- neither may be approximated from mean/median or an assumed parametric family.

Distribution metrics may be added only through a separately verified lossless join to the exact frozen source V1 distribution.

## Market benchmark and incremental information

The sportsbook remains the benchmark.

This first evaluator reports like-for-like paired model-vs-market point and probability scores plus disagreement diagnostics. Formal claims of incremental information require a separately reported matched analysis with enough games to avoid treating correlated props as independent. One Sunday is insufficient for a durable superiority claim.

## Uncertainty

Paired model-minus-market metric differences use game-clustered bootstrap intervals with:

- bootstrap unit: game ID;
- replicates: 5,000;
- seed family rooted at `20260919`, matching the frozen Shadow grading program.

No result from a single week authorizes promotion.

## Output separation

Postgame outputs are written to a separate evaluation directory/artifact. The evaluator must never mutate:

- `challenger_outputs/props21/forecast_originals.jsonl`;
- `challenger_outputs/props21/public_challenger.json`;
- V1 history;
- Market Anchor / Shadow A / Shadow B receipts;
- F-ST or winner-model artifacts.
