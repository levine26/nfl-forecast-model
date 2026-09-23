# Red-Team and Leakage Checklist

Status: MANDATORY FOR PHASE 2

Phase 2 may not execute outer Q1/Q2/Q3 development until the synthetic grading and chronology checks below pass.

## A. Line sign and ATS grading

### Required synthetic cases

Using canonical `R=M+L`:

| Home quote | M | Expected R | Expected home result |
|---|---:|---:|---|
| -3.0 | +4 | +1 | COVER |
| -3.0 | +3 | 0 | PUSH |
| -3.0 | +2 | -1 | LOSS |
| +3.0 | -2 | +1 | COVER |
| +3.0 | -3 | 0 | PUSH |
| +3.0 | -4 | -1 | LOSS |
| -3.5 | +4 | +0.5 | COVER |
| -3.5 | +3 | -0.5 | LOSS |
| +3.5 | -3 | +0.5 | COVER |
| +3.5 | -4 | -0.5 | LOSS |

Required assertions:

- favorite sign is never flipped twice;
- sportsbook `L` and model-implied `S=-L` remain separately named;
- home/away grading swaps cover/loss and preserves push;
- half-point lines produce no push;
- quarter-point/nonstandard lines are rejected, not rounded.

## B. Market-horizon leakage

- [ ] A later/closing line is never used as an earlier T-120 feature.
- [ ] Historical generic schedule line is not labeled T-120.
- [ ] T-120 source row timestamp is `<= kickoff-120m`.
- [ ] Stale-but-eligible earlier quote is preferred over any later quote.
- [ ] No later consensus is used to define an earlier consensus.
- [ ] CLV comparison source is kept separate from prediction-source fields.

Synthetic test: create two market snapshots for one game, one 130 minutes before kickoff and one 110 minutes before; T-120 selector must choose the 130-minute snapshot.

## C. Chronology/model fitting

- [ ] No random K-fold/shuffle.
- [ ] Inner validation season t is trained only on seasons `<t`.
- [ ] Outer season Y is trained/tuned only on seasons `<Y`.
- [ ] Imputation/scaling statistics are training-only.
- [ ] Q1 outer prediction is not used to tune Q1.
- [ ] Q2 consumes OOF/forward Q1 for every inner/outer row.
- [ ] Q3 consumes OOF/forward Q1/Q2 for every inner/outer row.
- [ ] Temperature scaling is fitted only from prior OOF logits.
- [ ] Blend weight is fitted only from prior OOF probabilities.
- [ ] No same-row prediction/calibration fit.

Required machine assertion: every prediction row carries `max_training_season < prediction_season` for outer evaluation and analogous fold timestamps for inner OOF rows.

## D. Distribution/key-number leakage

- [ ] No target-season residual scale.
- [ ] No target-season key-number frequency.
- [ ] No target-season empirical residual PMF.
- [ ] Key deltas learned only from prior eligible history.
- [ ] PMF normalizes to 1 within numerical tolerance.
- [ ] Endpoint bins absorb tail mass.
- [ ] Whole-number push equals exact PMF mass at market boundary.
- [ ] Half-point push is exactly zero.

Synthetic PMF test: use a toy normalized integer PMF and verify cover/push/loss sums match manual calculations at -3, -3.5, +3, +3.5.

## E. Outcome/feature leakage

- [ ] No final score/margin/ATS result appears in model feature columns.
- [ ] No postgame PBP enters a pregame row via unshifted rolling state.
- [ ] No postgame injury/starter state is attached to a pregame candidate.
- [ ] No completed 2026 outcome appears in architecture/tuning/development data.
- [ ] Current-season completed W/L convenience logic in production feature code is not reused in a way that violates the 2026 firewall.
- [ ] Schedule/result joins are audited for as-of semantics.

Required 2026 firewall test: any Phase-2 development dataset with `season==2026` and a non-null outcome must fail fast.

## F. Price/vig errors

- [ ] American-odds sign conversion matches frozen formulas.
- [ ] Home price applied only to home wager; away price only to away wager.
- [ ] Two-sided no-vig normalization uses matched book/line/timestamp pairs.
- [ ] Missing opposite-side price prevents paired no-vig computation.
- [ ] Missing spread-side price is never filled with -110.
- [ ] Push contributes zero profit/loss.
- [ ] Positive odds payout formula is tested separately from negative odds.

Synthetic odds tests:

- -110 -> decisive break-even 11/21;
- -120 -> 120/220;
- +100 -> .5;
- +150 -> .4;
- model probabilities .55/.05/.40 at -110 -> EV = `.55*(100/110)-.40` under unit risk.

## G. Duplicate/mapping integrity

- [ ] One canonical game ID per scheduled game.
- [ ] No duplicated game row after market/team-feature joins.
- [ ] Home/away teams match schedule identity.
- [ ] Outer evaluation does not count the same game twice due to multi-book rows; consensus/book selection occurs before game-level evaluation unless a specifically priced-book analysis is declared.
- [ ] Neutral/international venue does not silently flip home identity.

## H. Model-family/threshold fishing

- [ ] Q1 only frozen alpha grid.
- [ ] Q2 only 10 frozen family/shrinkage configurations.
- [ ] Q3 only four frozen learner configurations.
- [ ] Blend only five frozen weights.
- [ ] No learner added after outer results.
- [ ] No new key number/bucket after results.
- [ ] No feature added/removed based on outer ATS.
- [ ] No search across 1%,2%,3%,4%,5% selective subsets.
- [ ] No ROI-derived betting threshold.

Required implementation guard: candidate registry enumerates all allowed configs and rejects an unregistered config in the official Phase-2 runner.

## I. Repeated holdout use

- [ ] 2022–2025 labeled development/non-pristine in every result artifact.
- [ ] Outer results are generated under one frozen Phase-1 spec.
- [ ] Any rerun caused by a bug records the old invalidated artifact and defect reason.
- [ ] No repaired/revised architecture is described as fresh validation on the same historical seasons.

## J. Selective-subset mining

- [ ] All-games, quoted-price positive-EV, top20 and top10 are the only official subsets.
- [ ] Top20/top10 selected within outer season.
- [ ] Rank variable is fixed before outcomes.
- [ ] No result-based side reversal.
- [ ] All subset N/wins/losses/pushes/uncertainty reported.

## K. Calibration leakage

- [ ] Reliability diagrams are evaluation only.
- [ ] Outer calibration intercept/slope never feeds prediction adjustment.
- [ ] Q3 temperature comes only from prior OOF.
- [ ] No isotonic fit on in-sample training predictions.
- [ ] No per-key calibration correction fit on outer results.

## L. Protected production surfaces

Before merge of any Phase-2 research PR:

- [ ] `src/nfl_forecast/pipeline.py` unchanged unless separately authorized;
- [ ] `src/nfl_forecast/models.py` unchanged unless research-only change is explicitly isolated/authorized;
- [ ] `src/nfl_forecast/features.py` production behavior unchanged;
- [ ] `src/nfl_forecast/publish.py` unchanged;
- [ ] `src/nfl_forecast/market.py` and `market_t120.py` production semantics unchanged unless separate approved source work;
- [ ] `site/` and production `outputs/` unchanged;
- [ ] F-ST identity/weights unchanged;
- [ ] Sunday Signal forecast behavior unchanged.

## M. Required pre-run receipt

Before the first official Phase-2 outer run, save a machine/human-readable receipt containing:

- merged Phase-1 commit SHA;
- exact candidate registry/config hash;
- exact dataset provenance hash/version;
- eligible seasons/counts before outcomes are summarized;
- fold registry;
- package versions;
- code commit SHA;
- explicit `completed_2026_outcomes_used=false`;
- synthetic test status.

If any red-team item fails, fix the implementation and re-run tests **before** viewing official outer candidate results.