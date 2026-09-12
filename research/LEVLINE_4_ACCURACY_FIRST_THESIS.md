# LevLine 4.0 — Accuracy-First Research Thesis

Status: **research-only decision-policy addendum / no production change**  
Date: **2026-09-12**

## Executive conclusion

The product objective is now explicit: **maximize straight-up NFL winner accuracy first**. Brier score, log loss and calibration remain important, but they are secondary diagnostics and tie-breakers rather than the primary promotion objective.

This does **not** mean LevLine should train by naively maximizing in-sample or rolling empirical accuracy. The historical artifact provides a strong warning against that approach. The previously tested adaptive models whose weight-selection objective was labeled `accuracy` achieved only about 66.3%–66.7% winner accuracy over the common 1,087-game 2022–2025 sample, materially below both the raw market (~67.62%) and frozen F-ST reconstruction (~68.08%). Their selected PURE/market weights also swung sharply across seasons. Directly optimizing a coarse 0/1 objective was therefore less stable than regularized probability-oriented fitting.

The practical thesis is therefore:

> **Train with stable, classification-calibrated, chronologically validated surrogate objectives; select and promote models primarily by out-of-sample winner accuracy.**

That distinction lets LevLine pursue the user's real objective without throwing away statistical efficiency during training.

## 1. Why winner accuracy can legitimately be primary

Forecast evaluation should be aligned with the decision the forecast is meant to support. In LevLine's case the principal public output is a winner pick. For symmetric win/loss utility, the relevant operational loss is zero-one loss: the forecast is either correct or incorrect. A 0.5 probability threshold is the Bayes decision boundary when the underlying probability estimate is honest and the cost of the two error types is equal.

Proper scoring rules remain scientifically useful because they reward truthful probabilities and carry much more information per observation than a binary correct/incorrect label. They therefore remain valuable training surrogates, diagnostics and confidence-quality checks. But if two models have meaningfully different out-of-sample winner hit rates, LevLine's product objective prefers the model with the higher hit rate.

Representative methodological support:

- Granger (2000), *Journal of Forecasting*, argues forecast evaluation should be linked to the decision problem and user's loss.
- Bartlett, Jordan & McAuliffe (2006), *JASA*, formalize classification-calibrated surrogate losses: tractable surrogate optimization can remain consistent with minimizing zero-one classification risk.
- Gneiting & Raftery (2007), *JASA*, establish the role of proper scoring rules for honest probabilistic forecasting; these remain useful as secondary LevLine diagnostics.
- Song, Boulier & Stekler (2007), *International Journal of Forecasting*, explicitly evaluate NFL systems by winner success rate and show the betting line is an exceptionally difficult benchmark.

## 2. The historical LevLine evidence changes the implementation strategy

The original F-ST research artifact contains a direct accuracy-optimization experiment. Across the common 1,087-game 2022–2025 evaluation set:

- raw market winner accuracy: ~67.62%;
- frozen F-ST reconstruction winner accuracy: ~68.08%;
- production-compatible adaptive logit model selected for accuracy: ~66.70%;
- opponent-adjusted adaptive logit model selected for accuracy: ~66.51%;
- QB-aware adaptive logit model selected for accuracy: ~66.42%;
- opponent-adjusted + QB-aware adaptive logit model selected for accuracy: ~66.33%.

The season-by-season accuracy-selected weights were unstable. For example, the combined opponent-adjusted + QB-aware accuracy objective selected roughly 90% PURE in 2022 and 2023, then only 25% PURE in 2024 and 2025. That is exactly the sort of small-sample threshold instability expected from a discontinuous zero-one objective.

Therefore **accuracy should be the evaluation target, not a license for unconstrained accuracy grid-searching**.

## 3. The decisive statistic is the disagreement set

Suppose models A and B make the same pick in a game. That game contributes equally to their winner accuracy regardless of the probability confidence. It cannot change which model has the better hit rate.

Only games in which the two models choose different winners can change the accuracy ranking.

For challenger C versus incumbent I define:

- `C_only_correct`: challenger correct, incumbent wrong;
- `I_only_correct`: incumbent correct, challenger wrong;
- `discordant_games = C_only_correct + I_only_correct`;
- `switch_win_rate = C_only_correct / discordant_games`.

The overall accuracy difference is exactly:

`(C_only_correct - I_only_correct) / all_paired_games`.

This should become the centerpiece of accuracy-first LevLine evaluation. For a later horizon, the key football question becomes:

> When T-60/T-45/T-30 actually flips the T-120/3.0 pick, is the later pick right more than half the time?

This is much more interpretable than asking whether average Brier moved by a few ten-thousandths.

## 4. Statistical consequence: accuracy is much noisier than Brier

Winner accuracy discards probability information, so small genuine improvements require large samples to establish statistically.

At an underlying hit rate around 68%, an ordinary binomial 95% half-width is approximately:

- 200 games: ±6.5 percentage points;
- one 272-game regular season: ±5.5 points;
- 1,087 games: ±2.8 points;
- 2,000 games: ±2.0 points;
- 5,000 games: ±1.3 points.

Paired comparison helps because only discordant picks contribute to the difference, but modest gains can still require multiple seasons. Under a simple McNemar power approximation with 10% pick disagreement, an overall +1 percentage-point accuracy edge can require on the order of 7,800 paired games for conventional 80% power; +2 points roughly 2,000 games. Week clustering can make effective information smaller.

Therefore the existing 200-game/14-week gate remains only an **earliest checkpoint**. It cannot be interpreted as enough evidence to resolve a small winner-accuracy difference.

Relevant inference literature includes clustered matched-pair extensions of McNemar testing (Durkalski et al., 2003; Yang, Sun & Hardin, 2010), power calculations for clustered McNemar designs (Gönen, 2004; Wu, 2018), and multiple-McNemar procedures with correlation-aware bootstrap alternatives (Westfall et al., 2010).

## 5. Revised LevLine 4 horizon thesis

The strict-PIT architecture remains unchanged:

- T-120;
- T-60;
- T-45;
- T-30;
- no observation later than the nominal cutoff;
- no later-horizon backfill;
- no retrospective inactive reconstruction.

But the primary timing question becomes **winner correctness**, not probability loss.

For the all-four complete-case sample, report:

1. winner accuracy at each horizon;
2. accuracy delta versus frozen T-120 F-ST;
3. every pairwise horizon accuracy delta;
4. number and rate of pick disagreements;
5. switch win rate on disagreement games;
6. week-block uncertainty for paired correctness differences;
7. Brier/log loss/calibration secondarily.

If T-45 has better Brier but does not improve winner accuracy, that is not sufficient to replace 3.0 under the new product objective.

If T-45 improves winner accuracy and Brier is slightly worse, the accuracy gain gets priority unless probability quality breaches a separately frozen safety guardrail.

## 6. Probability and pick layers should be decoupled

A useful architectural refinement follows from the objective change.

LevLine should conceptually separate:

1. **pick layer** — chooses the winner and is evaluated primarily by zero-one loss;
2. **confidence layer** — assigns a probability to that chosen side and is evaluated by Brier/log loss/calibration.

Calibration should preferably be **pick preserving**: a post-processing map should not move a game across the 50% winner boundary unless that recalibrated system is explicitly registered as a new accuracy candidate.

This lets LevLine improve probability presentation without sacrificing a winner decision that has already earned its place on accuracy.

## 7. Promotion rule under the accuracy-first thesis

For a challenger to replace 3.0 as the principal winner engine:

1. compare on the exact same prospectively eligible games;
2. challenger winner-accuracy point estimate must exceed 3.0;
3. paired week-aware uncertainty must support a genuine positive accuracy difference before LevLine claims superiority;
4. analyze the disagreement set and require the challenger to win the switches, not merely inherit agreement games;
5. Brier/log loss/calibration are secondary safety diagnostics;
6. if accuracy remains unresolved, **retain 3.0** rather than replacing it because another model has prettier probabilities;
7. no material candidate redesign after viewing current-season results.

The previously registered +0.0025 Brier noninferiority margin can serve as an initial secondary probability-quality guardrail because it predates this accuracy-first policy. It is not the optimization target.

## 8. Current conclusion

The new thesis does not imply that LevLine should become a crude classification model. In fact, the repository shows the opposite: historical attempts to optimize adaptive weights directly for accuracy were worse and much less stable than the probability-oriented stack.

The strongest research strategy is:

**stable probabilistic/surrogate training + accuracy-first prospective model selection + disagreement-set analysis + secondary probability-quality guardrails.**

This is a material refinement of LevLine 4.0, but it does not change production. `F-ST-01-FROZEN-2026` remains the incumbent until a prospectively frozen challenger demonstrates a higher sustainable winner hit rate.
