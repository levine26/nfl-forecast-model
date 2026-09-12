# LevLine 4 — Conditional Market Reliance / Upset-Switch Thesis

Status: **research only / no production change**  
Date: **2026-09-12**

## Conclusion

A global 75% PURE / 25% market winner rule is not supported by LevLine's historical evidence. The rational accuracy-first successor is **not another fixed blend**. It is a selective, strongly regularized switch model that preserves the incumbent winner by default and asks whether specific point-in-time evidence is strong enough to justify changing that winner.

The goal is not to manufacture more underdog picks. The goal is to identify the subset of apparent market favorites whose quoted probability is plausibly inflated by stale priors, reputation/anchoring, recent-result salience, or matchup/context information that LevLine captures better than the market.

## Historical motivation

On the common 1,087-game 2022–2025 sample:

- market: 735/1,087 = 67.62%;
- PURE: 701/1,087 = 64.49%;
- production-like 75% PURE / 25% market: 716/1,087 = 65.87%;
- chronology-clean season-forward F-ST: 741/1,087 = 68.17%.

The 75% PURE / 25% market blend changed the market winner in 131 games and won only 56 of those switches while the market won 75. Its switch win rate was 42.7%, costing 19 net winners.

PURE itself disagreed with the market on 178 games and won only 72 of those switches (40.4%). Among games where the market favorite probability was at least 60%, blindly taking the PURE underdog won 14 of 35 (40%). At market favorite probabilities of at least 70%, it won only 1 of 6.

By contrast, the chronology-clean F-ST architecture disagreed with the market only 34 times, won those switches 20–14, and never changed the winner when the market favorite probability exceeded roughly 54%. Its historical edge was therefore a **selective decision-boundary correction**, not generalized favorite fading.

These facts reject two simplistic theses:

1. `PURE is better at identifying upsets, so increase PURE weight globally.`
2. `Popular / elite teams are overpriced, so fade strong favorites.`

Neither is supported as a universal rule.

## Why the user's super-team hypothesis is still scientifically plausible

Published NFL betting research does document behavioral channels that can create temporary mispricing:

- recency and overreaction to salient recent outcomes;
- anchoring to preseason Super Bowl odds throughout the regular season;
- some NFL moneyline evidence of reverse favorite-longshot bias (favorites overbet / underdogs underbet), although that effect varies materially by season;
- market failures around specific contextual variables such as unusual weather or travel/acclimation conditions.

That evidence makes a **conditional reputation/anchoring residual** worth testing. It does not justify a blanket underdog bonus.

## Proposed architecture

### Layer 1 — incumbent winner

Start with the frozen T-120 F-ST winner. Later raw market, F-ST-at-horizon, player state, contextual intelligence and other challengers do not automatically replace it.

### Layer 2 — switch gate

Estimate whether the incumbent winner should be flipped using only pregame information available at the candidate horizon.

Candidate explanatory variables may include, if sourced under a qualified point-in-time contract:

- contemporaneous no-vig market probability;
- PURE-versus-market logit disagreement;
- agreement/disagreement among independent PURE submodels;
- opening-to-current market movement and cross-book dispersion;
- preseason Super Bowl / season-win expectation as a reputation/anchor proxy;
- recent-result salience or streak variables constructed only from prior games;
- official QB/player availability and replacement burden;
- rest differential, travel distance, time-zone crossing, international-game acclimation and neutral-site state;
- matchup residuals already qualified under the research firewall.

The model should be regularized and trained with a smooth classification-calibrated surrogate. It should be *selected* by prospective paired winner accuracy / switch quality.

### Layer 3 — confidence

Probability confidence is evaluated separately with Brier, log loss and calibration. A probability-calibration change must not silently change the winner unless registered as a separate switch candidate.

## Primary estimand

The primary question is not `does this model have a lower Brier score?`

It is:

> When the switch gate changes the incumbent winner, does the new winner beat the incumbent on those disagreement games?

Report:

- challenger-only correct;
- incumbent-only correct;
- disagreement rate;
- switch win rate;
- overall accuracy delta;
- week-block paired uncertainty;
- secondary Brier/log-loss/calibration diagnostics.

## Guardrails

- No generic underdog bonus.
- No generic `super-team` penalty.
- No threshold selected from 2026 completed outcomes.
- No post-hoc conditional subgroup rescue after seeing live results.
- No use of later-horizon information in earlier-horizon forecasts.
- No production change without explicit authorization.
- Historical 2022–2025 slices are hypothesis-generating only; a candidate specification must be frozen before its prospective evaluation begins.

## Rams–49ers implication

A one-game upset should not cause global reweighting. The useful lesson from a result such as the 2026 Rams–49ers Australia game is that a fixed football/market blend can miss **situational asymmetry** that is not reducible to team strength alone. Travel/acclimation is therefore a more rational prospective feature family than simply increasing the weight on an underdog-facing PURE probability after the upset occurs.

## Denver–Kansas City implication

If PURE favors Denver while the market favors Kansas City, that disagreement is valuable research information, but historical evidence says `PURE disagrees` is not enough by itself to justify an override. The candidate should ask *why* PURE disagrees and whether the game contains the predeclared contextual/reputation signals associated with prior market misses.

## Final thesis

**Do not optimize a universal football/market percentage. Optimize the decision of when to trust the market and when to override it.**
