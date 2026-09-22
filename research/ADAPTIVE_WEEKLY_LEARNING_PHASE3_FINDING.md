# LevLine Adaptive Weekly Learning — Phase 3 Initial Finding

Status: **historical walk-forward finding / research integration only / no production change**  
Governance source: `research/ADAPTIVE_WEEKLY_LEARNING_RESEARCH_PLAN.md`  
Historical target sample: 2022–2025, 1,087 games  
Incumbent: chronology-clean frozen F-ST reconstruction  
2026 outcomes used for candidate fitting or selection: **0**

## Executive finding

The first preregistered weekly-learning experiment does **not** support changing LevLine's winner engine from frozen F-ST to an outcome-driven weekly learner.

The chronology-clean incumbent reproduces at:

- **741 / 1,087 correct**
- **68.1693% winner accuracy**
- Brier ≈ **0.210652**
- log loss ≈ **0.608710**

Three distinct forms of weekly adaptation were tested against that same paired sample:

| Candidate | Correct | Accuracy | Delta vs F-ST | Winner switches | Switch record vs F-ST |
|---|---:|---:|---:|---:|---:|
| Frozen F-ST | 741 | 68.169% | — | — | — |
| Naive weekly F-ST refit | 739 | 67.985% | **−0.184 pp** | 6 | 2–4 |
| Bayesian residual-state V1 | 722 | 66.421% | **−1.748 pp** | 121 | 51–70 |
| Residual V1 + selective gate | 738 | 67.893% | **−0.276 pp** | 79 | 38–41 |

The pick-preserving online calibration ablation intentionally made zero winner changes:

- correct: **741 / 1,087**
- winner accuracy: **68.169%**
- Brier: ≈ **0.210568** (small improvement)
- log loss: ≈ **0.608626** (small improvement)

This suggests a useful separation: **weekly outcome information may have modest probability-calibration value while failing to improve winner selection.**

## 1. Naive weekly full refit negative control

The negative control refits the same two-input market/PURE logistic stack before every target week using every completed prior game, including earlier weeks of the current season.

It is chronology-safe: Week t never uses a Week t outcome.

Result:

- frozen F-ST: 741 correct;
- weekly refit: 739 correct;
- delta: **−2 winners / −0.184 percentage points**;
- disagreements: 6;
- weekly-refit-only correct: 2;
- F-ST-only correct: 4;
- switch win rate: **33.3%**.

Season breakdown:

- 2022: 181 vs 182 (−1);
- 2023: 184 vs 185 (−1);
- 2024: 195 vs 195 (0);
- 2025: 179 vs 179 (0).

Probability quality moved slightly in the opposite direction from winner accuracy:

- Brier: ~0.210574 vs ~0.210652 for frozen F-ST;
- log loss: ~0.608633 vs ~0.608710.

**Disposition: reject weekly full refitting as a winner-accuracy improvement.** It may be studied separately as a probability-calibration phenomenon, but it does not earn winner-engine changes.

## 2. Bayesian residual-state V1

The V1 adaptive state starts from F-ST log-odds and learns persistent team residuals only after each completed week. Every game in a week is scored from the same preweek state; outcomes are batch-applied after all forecasts are frozen.

Frozen V1 parameters were:

- initial variance: 0.20;
- process variance/week: 0.03;
- weekly mean reversion: 0.97;
- offseason mean reversion: 0.50;
- max absolute residual state: 1.00 logit.

Result:

- adaptive correct: **722 / 1,087**;
- accuracy: **66.421%**;
- delta: **−19 winners / −1.748 pp**;
- winner switches: 121;
- adaptive-only correct: 51;
- F-ST-only correct: 70;
- switch win rate: **42.15%**;
- Brier and log loss both deteriorated.

Season deltas in correct winners:

- 2022: −5;
- 2023: −10;
- 2024: −7;
- 2025: +3.

The isolated positive 2025 result does not overcome the unstable and materially negative multi-season record.

**Disposition: reject ADAPTIVE-RESIDUAL-STATE-V1.**

## 3. Conservative selective switch gate

The preregistered V1 gate permits an adaptive winner switch only when:

- F-ST is within 7.5 probability points of 50%; and
- the residual learner moves probability by at least 3.5 points; and
- the adaptive forecast crosses to the opposite winner.

Result:

- correct: **738 / 1,087**;
- accuracy: **67.893%**;
- delta: **−3 winners / −0.276 pp**;
- authorized switches: 79;
- challenger-only correct: 38;
- F-ST-only correct: 41;
- switch win rate: **48.10%**.

The gate substantially reduced the damage of the raw residual state, but it did not create positive winner value.

**Disposition: reject ADAPTIVE-SELECTIVE-SWITCH-GATE-V1 as a winner challenger.**

## 4. Pre-registered robustness grid

The robustness grid was committed to the governance ledger **before first integrated results were available**.

### Residual state: 27 configurations

Grid:

- process variance/week: [0.01, 0.03, 0.06];
- weekly mean reversion: [0.90, 0.97, 1.00];
- offseason mean reversion: [0.25, 0.50, 0.75].

**All 27 configurations underperformed frozen F-ST in winner accuracy.**

Best descriptive configuration:

- q = 0.01;
- weekly mean reversion = 0.90;
- offseason mean reversion = 0.25;
- correct: **737 / 1,087**;
- accuracy: **67.801%**;
- delta: **−4 winners / −0.368 pp**;
- switches: 56;
- switch record: 26–30.

Worst configuration:

- correct: 708 / 1,087;
- delta: about −3.04 pp.

Therefore the V1 failure is not plausibly explained by one unfortunate learning-rate choice.

### Selective gate: 9 configurations

Every preregistered boundary/shift combination also underperformed F-ST.

Best was the primary V1 gate itself:

- 738 / 1,087;
- −0.276 pp.

No gate sensitivity result provides historical evidence for promotion.

## 5. Nested chronology-safe parameter selection

To test whether adaptive parameter choice could itself learn over time without target leakage, the predeclared residual grid was selected using only earlier target seasons and then scored on the next untouched season.

Results:

- target 2023: selected configuration lost **6 winners** vs F-ST;
- target 2024: selected configuration lost **2 winners**;
- target 2025: selected configuration lost **2 winners**.

Thus even chronology-safe adaptive parameter selection failed to rescue the residual-state concept.

## 6. Calibration ablation

The online calibration layer fits only a strongly regularized logit intercept from prior weeks. The primary variant is pick-preserving: it cannot cross the 50% winner boundary.

Result:

- winner record unchanged at 741–346;
- Brier improved by about **0.000084**;
- log loss improved by about **0.000084**.

This is small, but directionally coherent and costs zero winner decisions by construction.

**Disposition: retain calibration-only research as a probability-quality lane; do not describe it as a winner-accuracy improvement.**

## 7. Scientific interpretation

The experiment now provides direct LevLine-specific evidence against the broad hypothesis:

> "LevLine should become more accurate simply by learning from its own previous weekly outcomes."

The evidence instead supports a narrower interpretation:

1. Frozen F-ST already captures enough stable market/PURE structure that weekly global coefficient refitting adds little and slightly harms the 0/1 winner decision.
2. Team-level forecast residuals are noisy; treating them as persistent latent strength causes too many incorrect switches.
3. Conservative winner gating reduces damage but does not turn outcome-driven residuals into positive signal.
4. Weekly outcomes can contain small calibration information without containing useful winner-boundary information.
5. If LevLine is to earn additional winner accuracy, the next challenger should rely on **orthogonal point-in-time information** — e.g. component-resolved boundary information, qualified QB/personnel shocks, and strict-PIT market microstructure — rather than merely feeding its prior misses back into the winner model.

## 8. Governance disposition

- **Do not modify production F-ST.**
- **Do not rescue V1 by post-hoc parameter tuning.**
- **Do not freeze a prospective winner challenger from these losing candidate families.**
- Continue adversarial validation/reproducibility for the recorded result.
- Any materially new adaptive winner mechanism receives a new candidate ID and, if informed by these results, cannot claim this same historical sample as independent confirmation.
- The probability-calibration layer may continue as a separate, pick-preserving research lane.

## 9. Prior update

The original research prior was approximately +0.6 pp expected winner uplift from a properly constrained adaptive weekly layer.

The historical experiment materially weakens that prior **for outcome-driven weekly learning**. The evidence does not eliminate the possibility that a different adaptive system using genuinely orthogonal pregame information can add value, but it argues strongly against forecasting a winner-accuracy gain from self-retraining alone.

No production change is authorized by this finding.
