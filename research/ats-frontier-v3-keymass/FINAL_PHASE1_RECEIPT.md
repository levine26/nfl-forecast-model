# Final Phase 1 Receipt

Status: `COMPLETE`.

## Identity and immutable boundary

- Program: `LEVLINE ATS FRONTIER V3 — KEY-MASS PROSPECTIVE PROGRAM`
- Candidate: `FV3-PROS-KMASS-01`
- Strong null: `FV3-NULL-STUDENTT-CONSTANT-01`
- Scientific freeze: `2026-09-24T19:04:04Z`
- Opening main: `660d1bfc87001d9141ab030ed8f053a875bee3a2`
- Implementation branch: `research/ats-frontier-v3-keymass-phase1`
- Implementation PR: `#580`
- Exact validated implementation head: `99934841edccc8914731d02392eef0e49686a6de`
- Implementation merge SHA: `807ecfbc8346c79ec635eb0ec6437c137b1a6a78`
- Merged main verified at: `807ecfbc8346c79ec635eb0ec6437c137b1a6a78`

V2 remains immutable prior evidence: M3 and M4 are `REJECTED`; historical V2 Phase 6 is `NOT_AUTHORIZED`; `CONSTANT_SCALE_KEY` is `FUTURE_VERSION_HYPOTHESIS_ONLY`. No V2 historical result is treated as V3 confirmation.

## Frozen scientific design

Candidate and null share the T-120 market center, Student-t family, degrees of freedom, constant scale, chronology, exact integer-bin integration, unbounded tails, and cover/push/loss translation. The candidate differs only by finite log-mass offsets at `0`, `|3|`, and `|7|`, followed by analytic normalization over the full integer lattice. There is no hard support, clipping, endpoint folding, conditional scale, extra football feature family, extra key number, skew family, or mixture rescue.

Historical development/training is fixed to NFL regular-season 2010–2025. Student-t degrees of freedom are selected from `{4,6,10,30}` using null-only forward-season validation over 2016–2025. One shared constant scale is then fit by null integer-margin maximum likelihood on all 2010–2025 development rows. Holding df and scale fixed, the candidate fits only `gamma0`, `gamma_abs3`, and `gamma_abs7` with frozen L2 regularization `lambda=10`. Prospective refitting during the initial validation period is prohibited.

## Operational market contract

- Provider: `The Odds API`
- Region: `us`
- Horizon: `T-120m`
- Selector: latest qualifying capture at or before kickoff minus 120 minutes and no more than 7.5 minutes early
- Minimum consensus: two unique valid sportsbooks
- Raw spread consensus: median home spread point across qualifying books
- Canonical expected-home-margin sign: negative of raw bookmaker home spread point
- After-horizon quote substitution: prohibited

An eligible prospective game must occur after the scientific freeze, have resolved event identity and a qualifying T-120 capture under the frozen timestamp/book-count contract, and have its immutable candidate/null record serialized before kickoff without outcome access. A missed T-120 horizon is not repaired retrospectively.

## Evaluation and stopping contract

Primary metric: paired exact integer-margin logarithmic-score delta, `candidate - null`; lower than zero is favorable.

Formal scientific evaluation is prohibited before the end of the 2027 regular season and requires at least 300 eligible games, 20 distinct season-week blocks, two seasons, and at least 64 eligible games in each represented season. Formal uncertainty uses 10,000 week-block bootstrap resamples with seed `20260924`, plus per-week/per-season contributions and leave-one-week-out concentration checks. There is no favorable early stop.

`ELIGIBLE_FOR_PRODUCTION_REVIEW` requires all minimum-data conditions, mean primary delta below zero, the paired 95% week-block-bootstrap upper bound below zero, each adequately sampled season below zero, and every leave-one-week-out pooled mean below zero. Mean delta at or above zero after minimum evidence is `REJECTED`; otherwise the result is `INCONCLUSIVE`. Production promotion is never automatic.

## Immutable prospective record

The Phase-1 contract requires game ID, season/week, kickoff timestamp, prediction timestamp, market provider, market horizon target, market request timestamp, maximum included quote timestamp, market event ID, source-book count/names, raw home spread, canonical home margin, available home/away spread prices, candidate PMF descriptor, null PMF descriptor, candidate cover/push/loss probabilities, null cover/push/loss probabilities, raw-input SHA256, model-code SHA256, config SHA256, and prediction SHA256. Duplicate `(candidate_id, game_id, horizon)` records are rejected.

## Exact-head validation

Exact head `99934841edccc8914731d02392eef0e49686a6de` passed:

- `ATS Frontier V3 Phase 1` — success; 8/8 frozen numerical/leakage/timestamp/immutability tests passed.
- `LevLine research firewall` — success.
- `LevLine research validation` — success across the repository validation matrix.

Validated frozen SHA256 values:

- `v3_keymass.py`: `53553d0b8014b6ba990a6e3157079f3cc70b9c960f4af78644af875dc9650e69`
- `fit_frozen_parameters.py`: `5de178e7578b776d3782322118722a067f5b46700ccd69b6a8c46a517620ea3c`
- `v3_config.json`: `1ba794458b402b59bd88f1bb35486759f4aa2e38e9340793544c648a4f1cadfb`
- `test_phase1.py`: `32dd59c8bf20c1654c173d486b6a66deadb9cb5ff86727ca658601a5670420d2`

## Parallel capture and firewalls

M1 `FV2-PROS-M1-MARKETSTATE-01`: existing governed prospective market capture remains active and separate.

M2 `FV2-PROS-M2-QBDELTA-01`: existing prospective T-120 QB1/QB-shock capture is preserved as partial active evidence; complete M2 field coverage is not certified, missing states must remain missing, and retrospective synthesis is prohibited.

Completed-2026 outcomes used for V3 candidate selection, architecture, training-rule choice, parameter tuning, threshold choice, or Phase-1 validation: `NO`.

Confirmatory outcome scoring performed in Phase 1: `NO`.

Production changed by V3 Phase 1: `NO`. `F-ST-01-FROZEN-2026`, Sunday Signal numerical forecasts, official fair spread, score projections, official ATS picks, public history/grading, and deployment remain outside V3.

## Phase 2 handoff

Phase 2 is `NOT_STARTED`. Its exact first action is to execute the frozen 2010–2025 parameter-estimation procedure once, persist and hash `frozen_parameters.json`, and then generate immutable candidate/null T-120 shadow forecasts for qualifying post-freeze games. That fit is development parameter estimation, not historical confirmation. No outcome scoring is authorized in that action.

The first potential eligible window identified at Phase-1 freeze was `2026_03_ATL_GB` on September 24, 2026, only if its governed T-120 snapshot satisfied the frozen contract; otherwise the next qualifying future game becomes the first prospective record.
