# LevLine Props 2.0 — Defensive Efficiency True-Pregame Result

Status: **RETROSPECTIVE TRUE-PREGAME ABLATION — RUSHING PASSED / RECEIVING PASSED**  
Primary workflow: `35419926356`  
Contract: `levline-props-v2-defensive-efficiency-pregame-v0.1.0`  
Production promotion authorized: **NO**

## Scientific question

Do the strictly lagged opponent defensive-efficiency residuals that passed component isolation
improve the complete pregame rushing-yard and receiving-yard predictive distributions when V1's
opportunity uncertainty is preserved exactly?

Rushing and receiving were independent preregistered hypotheses.

For both candidates:
- the frozen V1 pregame state was used;
- every sampled opportunity-count array was preserved;
- opponent defense state used only weeks strictly before the target week;
- residual coefficients were fit only through season S−1;
- only the relevant yards/event mean and yardage samples were regenerated;
- target-game opportunities and target-game yards were not used for fitting.

## Rushing — PASS

Immutable primary artifacts:
- 2023: `10576772742`
- 2024: `10577203041`
- 2025: `10577772014`

2023–2025 aggregate:
- N **941** rushing-yard props;
- 230 unique games;
- 112 unique players;
- V1 CRPS **18.19360**;
- challenger CRPS **17.93138**;
- challenger minus V1 CRPS **−0.26222**;
- game-clustered 95% CRPS-difference interval **−0.34455 to −0.17871**;
- V1 Fair-Line MAE **24.85228**;
- challenger Fair-Line MAE **24.56642**;
- challenger minus V1 MAE **−0.28587**;
- game-clustered MAE-difference interval **−0.41022 to −0.16561**;
- V1 80% coverage **62.17%**;
- challenger 80% coverage **62.91%**.

Season-level CRPS differences:
- 2023: **−0.55083**
- 2024: **−0.13786**
- 2025: **−0.23052**

Season-level Fair-Line MAE differences:
- 2023: **−0.64232**
- 2024: **−0.12895**
- 2025: **−0.27397**

Frozen rushing gate:
- pooled CRPS improves: **PASS**
- pooled Fair-Line MAE improves: **PASS**
- at least two seasons improve CRPS: **PASS (3/3)**
- pooled clustered CRPS CI upper bound <= 0: **PASS**
- coverage deterioration <= 1.5 pp: **PASS** (coverage improves approximately +0.74 pp)

Directional diagnostic on paired decided rows:
- N **940**
- V1 direction accuracy **48.51%**
- challenger direction accuracy **48.09%**
- change approximately **−0.43 pp**

**RUSHING DISPOSITION: ADVANCE TO PROSPECTIVE SHADOW ELIGIBILITY.**

## Receiving — PASS

Immutable primary artifacts:
- 2023: `10577742093`
- 2024: `10577352677`
- 2025: `10577372249`

2023–2025 aggregate:
- N **1,864** receiving-yard props;
- 230 unique games;
- 256 unique players;
- V1 CRPS **19.18091**;
- challenger CRPS **18.77232**;
- challenger minus V1 CRPS **−0.40859**;
- game-clustered 95% CRPS-difference interval **−0.50123 to −0.32632**;
- V1 Fair-Line MAE **26.87741**;
- challenger Fair-Line MAE **26.31626**;
- challenger minus V1 MAE **−0.56116**;
- game-clustered MAE-difference interval **−0.68187 to −0.44671**;
- V1 80% coverage **71.51%**;
- challenger 80% coverage **71.78%**.

Season-level CRPS differences:
- 2023: **−1.08240**
- 2024: **−0.21107**
- 2025: **+0.09244**

Season-level Fair-Line MAE differences:
- 2023: **−1.40890**
- 2024: **−0.30560**
- 2025: **+0.00704**

Frozen receiving gate:
- pooled CRPS improves: **PASS**
- pooled Fair-Line MAE improves: **PASS**
- at least two seasons improve CRPS: **PASS (2/3)**
- pooled clustered CRPS CI upper bound <= 0: **PASS**
- coverage deterioration <= 1.5 pp: **PASS** (coverage improves approximately +0.27 pp)

Directional diagnostic on paired decided rows:
- N **1,859**
- V1 direction accuracy **50.13%**
- challenger direction accuracy **49.81%**
- change approximately **−0.32 pp**

**RECEIVING DISPOSITION: ADVANCE TO PROSPECTIVE SHADOW ELIGIBILITY.**

## Interpretation

This is the strongest Props 2.0 football-model result to date because the mechanism improves both
proper distribution score and Fair-Line error **after restoring full pregame opportunity
uncertainty**.

However, this result must not be overstated:
- directional hit rate did not improve retrospectively;
- 2023–2025 has already been used during Props development;
- sportsbook line MAE remains a separate market benchmark;
- retrospective success cannot establish economic betting edge.

The correct next step is a prospectively frozen shadow challenger using these defense residuals,
with no outcome-tuned blending or thresholds.

## Production disposition

**NO PRODUCTION PROMOTION.**

Both defensive-efficiency mechanisms become eligible for the future prospective shadow challenger
under `PROPS_V2_COMBINATION_POLICY.md`.

No F-ST model, published Props V1 output, Sunday Signal forecast, probability calibration, betting
threshold, or market policy changes from this retrospective result.
