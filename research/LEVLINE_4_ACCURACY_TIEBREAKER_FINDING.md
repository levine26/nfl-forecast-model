# LevLine 4 — Accuracy Tie-Breaker Finding

Status: **historical finding / prospective research implication / no production change**  
Date: **2026-09-12**

## Finding

Under a straight-up winner-accuracy objective, the historical proprietary value of the F-ST architecture is concentrated almost entirely at the winner decision boundary.

In the chronology-clean 2022–2025 evaluation:

- games: 1,087;
- F-ST architecture: 741 correct (68.17%);
- raw market: 735 correct (67.62%);
- F-ST net advantage: +6 correct (+0.55 percentage points);
- F-ST/market pick disagreements: 34 games (3.13% of the sample);
- F-ST won those disagreements 20–14 (58.82% switch win rate).

Every one of the 34 F-ST/market winner disagreements occurred when the raw market home-win probability was within 4 percentage points of 50%. The entire +6 net-win advantage therefore came from games the market itself viewed as close to a coin flip.

This result is directionally consistent with the frozen-final-coefficient reconstruction, where F-ST and market differed on only 25/1,087 games and F-ST won those switches 15–10.

## Interpretation

LevLine should not think of its proprietary modeling as needing to overturn strong market favorites in order to add winner-pick value. Historically it did not do that.

The market already determined the winner direction on roughly 97% of the common sample. LevLine's incremental winner accuracy came from acting as a **tie-breaker on marginal games**.

That suggests the highest-value question for LevLine 4 is not:

> Can a larger football model beat the market everywhere?

It is:

> When the incumbent winner decision is genuinely marginal, can later information and LevLine's residual signals choose the right side of the boundary more often?

## Accuracy geometry

For any challenger versus incumbent:

`accuracy gain = disagreement rate × (2 × switch win rate − 1)`.

Examples:

- 5% disagreement and 60% switch win rate -> +1.0 percentage point overall accuracy;
- 10% disagreement and 55% switch win rate -> +1.0 point;
- 3% disagreement and 66.7% switch win rate -> about +1.0 point.

This identity makes two requirements explicit. A useful LevLine 4 winner engine needs both:

1. enough genuinely informative pick changes to matter; and
2. a switch win rate above 50%.

Merely moving probabilities without changing the winner cannot improve straight-up accuracy.

## Consequence for T-120 / T-60 / T-45 / T-30 research

The prospective horizon experiment should retain the full all-game accuracy comparison, but the principal mechanism diagnostic should be the switch set versus T-120 F-ST.

For each later horizon report:

- how often the winner changes;
- challenger-only-correct versus incumbent-only-correct;
- switch win rate;
- net correct winners gained/lost;
- incumbent distance from the 50% boundary;
- whether the late market crossed 50%;
- magnitude of T-120-to-late market movement;
- point-in-time QB/inactive shock when qualified;
- Brier/log loss/calibration secondarily.

The first prospective contract does **not** create a post-hoc boundary-only switching rule. Boundary bins are diagnostic. If prospective results reveal a stable conditional switching mechanism, it requires a new frozen candidate ID and a fresh evaluation start.

## Training implication

This finding does not justify fitting directly on empirical 0/1 accuracy. LevLine's own historical accuracy-weight searches were materially worse and unstable.

The recommended approach remains:

**stable regularized probabilistic/surrogate training -> accuracy-first out-of-sample selection -> disagreement-set/switch analysis.**

This is consistent with classification theory: smooth classification-calibrated surrogate losses can be used for tractable fitting while zero-one loss remains the target decision risk.

## Final research implication

The most promising path to a meaningfully higher Sunday Signal hit rate is to improve **close-game decision quality**, especially after new information becomes available between T-120 and T-30, while leaving clear winner decisions alone unless a genuinely large information shock changes the game state.

No production forecast or current Sunday Signal pick is changed by this finding.
