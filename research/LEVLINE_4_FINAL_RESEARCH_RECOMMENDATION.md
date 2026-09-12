# LevLine 4.0 — Accuracy-Primary Architecture Recommendation

Status: **research-only / no production promotion authorization**  
Date: **2026-09-12**

This document supersedes the earlier proper-score-first architecture conclusion for the LevLine 4 research program. It does **not** rewrite historical preregistrations or authorize any production change. The frozen production model `F-ST-01-FROZEN-2026` remains immutable. No completed 2026 outcome was used to invent, tune, rescue, or select the architecture below.

## 1. Objective and selection rule

LevLine 4's primary objective is **sustainable out-of-sample straight-up NFL winner accuracy**.

Training may use smooth classification-calibrated objectives, regularization, Bayesian shrinkage, chronological fitting, and probability-oriented losses. Final winner-model selection, however, is driven primarily by paired winner accuracy and the quality of the model's decision-changing switches.

Brier score, log loss, calibration, margin accuracy, and probability coherence remain important diagnostics and guardrails. They are not the primary winner-selection criterion. Grossly incoherent or catastrophically overconfident probabilities remain unacceptable.

The architecture should separate:

- a **pick layer**, selected primarily for winner correctness; and
- a **confidence layer**, selected for probability quality while preserving the pick unless a separately registered winner candidate authorizes a side change.

## 2. Production remains frozen

`F-ST-01-FROZEN-2026` remains the immutable T-120 production/accountability forecast. LevLine 4 remains shadow research unless explicit later promotion is authorized.

Research code may not alter production coefficients, imports, runtime configuration, prediction locks, Sunday Signal behavior, grading, rollback boundaries, or production workflows.

## 3. Empirical starting point

On the common 2022–2025 historical sample of 1,087 games:

- raw market: 735/1,087 = 67.62%;
- chronology-clean aggregate F-ST architecture: 741/1,087 = 68.17%;
- component-resolved L2 stack using market logit plus `logistic`, `extra_trees`, `xgboost`, and `catboost` logits: 744/1,087 = 68.45%.

The component-resolved stack beat aggregate F-ST only 10–7 on 17 disagreement games. Its week-block uncertainty interval includes no advantage, so 68.45% is a promising point estimate rather than established superiority.

The architectural finding is stronger than the statistical superiority claim: **component resolution should be preserved through the winner-decision layer.** Collapsing football information into a single PURE value discards useful disagreement structure.

## 4. The decisive historical constraint: useful football overrides are boundary-local

The historical proprietary edge over the raw market is concentrated near the winner decision boundary.

The component-resolved stack's strongest market favorite override was only about 55.1%. It did not discover a general ability to fade clear favorites.

Generic contrarian rules fail:

- old production-like `75% PURE / 25% market` switched away from the market 131 times and lost those switches 56–75;
- all four football components unanimously opposing the market went 38–58 on those upset switches;
- adding strong preseason reputation to the favorite did not rescue the rule.

Therefore LevLine 4 must **not** be another universal football/market blend and must **not** use football unanimity, reputation, or team identity as a standalone upset trigger.

## 5. Recommended architecture: incumbent + two conditional gates

The strongest defensible architecture is an incumbent-preserving two-regime winner system.

### 5.1 Incumbent winner

Begin with the strongest qualified incumbent winner, anchored to frozen T-120 F-ST for production-accountability comparisons.

### 5.2 Boundary Gate

The Boundary Gate handles games where the market is near the decision boundary and the cost of a small probability error can change the winner pick.

This is currently the **only gate with affirmative historical evidence of useful side changes**.

Candidate inputs should remain compact and theory-driven:

- contemporaneous market logit;
- each qualified football component probability/logit;
- component vote count and sign agreement;
- mean football residual versus market;
- component dispersion/variance;
- maximum component residual;
- later strict-PIT market/player information only after those feature families are prospectively qualified.

Preferred model classes are sparse/L2 logistic gates, Bayesian shrinkage gates, monotonic/GAM variants, or similarly regularized classifiers. Avoid brute-force zero-one threshold mining and unconstrained trees on the small NFL sample.

The historical 68.45% component-resolved stack is a leading Boundary Gate candidate, not a production promotion.

### 5.3 Selective Upset Gate

The Upset Gate handles clear market favorites. Its default action is **preserve the incumbent**.

A stronger favorite requires stronger independent evidence before an override. The conceptual evidence burden should rise with market log-odds, for example monotonically with `abs(logit(P_market))`, rather than by mining arbitrary favorite bins.

A qualified upset signal should combine football disagreement with one or more plausibly orthogonal contemporaneous channels. Candidate channels are:

1. **same-book market-path corroboration** — movement toward the challenger across independent books, source overlap, dispersion/freshness, and movement breadth;
2. **authoritative player-state residual** — QB/role-weighted availability shock, replacement burden, uncertainty, time since publication, and the market response since that information arrived;
3. **dynamic-strength/regime evidence** — only if it adds winner-decision value after controlling for the contemporaneous market;
4. **circadian/travel or game-variance modifiers** — only as small interactions after historical/prospective qualification;
5. **reputation/anchoring** — interaction only, never a direct fade trigger.

No generic upset gate is currently qualified. Until orthogonal evidence wins prospective switches, the correct clear-favorite behavior is conservative incumbent preservation.

## 6. Disagreement-set evaluation is mandatory

For every challenger C versus incumbent I, report:

- challenger-only correct;
- incumbent-only correct;
- total disagreements;
- disagreement rate;
- switch win rate;
- overall accuracy delta;
- week-cluster uncertainty;
- season and leave-one-week-out stability.

The identity

`accuracy gain = disagreement rate × (2 × switch win rate - 1)`

must remain explicit. High overall agreement cannot hide bad switches, and a small number of excellent switches can be valuable even when aggregate metrics look nearly identical.

McNemar-style discordant inference and week/block bootstrap are preferred paired tools. A higher point estimate is not equivalent to established superiority.

## 7. Strict-PIT horizon and market-path research

Canonical horizons remain T-120, T-60, T-45, and T-30.

A nominal T-X state may use only information available **at or before** that cutoff. Valid timing error is early-only; positive timing error is ineligible. A missed horizon remains missing. Later horizons, closing prices, and later player states may not backfill earlier states.

The market-state research layer now preserves all four horizons and derives same-book microstructure features only from sportsbook rows belonging to the exact selected PIT consensus requests. This prevents changing sportsbook composition or retry mixing from masquerading as broad movement.

The key winner question is not whether a later probability has a better Brier score. It is:

> When later information changes the T-120 incumbent pick, does the later decision win the switch?

Report accuracy, switches versus T-120 F-ST, challenger-only wins, incumbent-only wins, switch win rate, accuracy delta, and week-cluster uncertainty at every horizon. Brier/log loss remain secondary diagnostics.

T-45 remains an operational hypothesis, not a selected winner.

Published NFL-inclusive evidence that pregame moneyline price changes exhibit negative autocorrelation (Simon, 2025, DOI `10.1177/15586235251394815`) justifies testing overreaction/reversal features, but does not justify an automatic line-movement fade.

## 8. Player-state lane

Point-in-time player capture is now sufficiently mature to support prospective residual research, but not outcome-tuned thresholds.

The target estimand is:

> What authoritative player-state information remains unpriced by the market at this exact horizon?

Do not double-count injury information already embedded in the price. The highest-value interaction is likely:

`football/player thesis × market response × elapsed time since authoritative news`.

Player information may change a pick only through a frozen candidate evaluated prospectively or through genuinely prior historical data that satisfy the same chronology contract.

## 9. Travel/rest/circadian lane is demoted to modifier status

Generic rest differential should not be a core upset trigger.

Lopez & Bliss (2024, DOI `10.3389/frbhe.2024.1479832`) find no significant modern bye or mini-bye competitive advantage and estimate that the historical bye advantage largely disappeared after the 2011 CBA. This makes a large universal rest adjustment scientifically difficult to justify.

Circadian/travel effects remain plausible but heterogeneous. Roy & Forest (2018, DOI `10.1111/jsr.12565`) report a westward evening-game disadvantage across major leagues but only a trend in the NFL subset. Treat time-zone/body-clock state as a small interaction candidate, not an automatic side switch.

## 10. Reputation/anchoring lane remains interaction-only

Fodor, Patterson & Shank (2025, DOI `10.1016/j.econlet.2025.112288`) provide NFL-specific evidence that preseason Super Bowl expectations influence bettor behavior and sportsbook closing lines through the season.

That supports preserving preseason reputation features. LevLine's own switch audit rejects a generic super-team fade, so reputation may only modify a richer upset-risk state.

## 11. Dynamic strength, score distributions, variance, and coaching

These remain challenger/diagnostic families rather than default winner-engine inputs.

A latent team-strength model can be valuable as a favorite-vulnerability detector even if its raw probabilities are inferior. A score model can be useful if variance/tail shape predicts when the incumbent favorite is fragile even when its mean win probability does not improve. Coaching/schematic features should be small, theory-driven interactions rather than a feature explosion.

Every such family must answer the same question: **does it improve the winner decision after controlling for the contemporaneous market/incumbent?**

## 12. 2026 firewall

Completed 2026 outcomes may grade only candidates frozen before the relevant games. They may not be used to invent thresholds, add features, select interactions, rescue failed candidates, or manufacture subgroups.

A theory inspired by a 2026 result receives a new candidate ID, frozen logic, and a fresh prospective start before it contributes promotion evidence.

## 13. Current research ranking

### Strengthened

1. **Component-resolved Boundary Gate** — strongest current historical point estimate; all useful changes remain boundary-local.
2. **Strict-PIT later market microstructure** — high-value prospective corroborator; now instrumented at T-120/T-60/T-45/T-30 with exact-request same-book breadth features.
3. **Player-state × market-digestion interaction** — data capture is viable; causal estimand is appropriately residual rather than raw injury value.

### Demoted or rejected

1. universal PURE/market weighting;
2. generic football-unanimity upset switches;
3. generic super-team/reputation fades;
4. generic modern rest advantage as a large standalone feature;
5. score-derived win probability as an automatic winner-engine input;
6. complexity added without demonstrated switch value.

### Unresolved

1. a true Selective Upset Gate for clear favorites;
2. whether T-60, T-45, or T-30 adds winner value over T-120;
3. whether market movement should be followed, faded, or interpreted conditionally;
4. whether player information creates residual winner value after market digestion;
5. whether dynamic strength, variance, circadian, or coaching interactions improve favorite-vulnerability detection.

## 14. Immediate experiments

The next evidence cycle should prioritize uncontaminated prospective collection rather than more arbitrary model families:

1. collect strict-PIT market snapshots at all four horizons with book identity and freshness;
2. evaluate consensus movement **and same-book breadth** on disagreement/switch games;
3. join authoritative player-state timestamps to market movement and elapsed-time features;
4. freeze compact Boundary Gate and Upset Gate candidate families before grading future games;
5. continue historical work only where genuinely prior chronology can validate a theory without reusing 2022–2025 as both discovery and proof;
6. rank candidates by paired winner improvement, with Brier/log loss/calibration as guardrails;
7. preserve the frozen production firewall until explicit promotion criteria are met.

## 15. Current conclusion

The best realistic path above the current ~68.2% incumbent is **not broader contrarianism**. It is selective decision replacement:

`frozen incumbent winner`

`+ component-resolved Boundary Gate`

`+ strict-PIT later market/player corroboration`

`+ default-off Selective Upset Gate whose evidence burden rises with favorite strength`

`+ separate confidence/calibration layer`.

The Boundary Gate is historically supported but not statistically proven superior. The Upset Gate remains intentionally conservative because historical generic upset logic loses. LevLine 4 should earn additional wins by making **fewer, better switches**, not by finding more reasons to disagree with the market.
