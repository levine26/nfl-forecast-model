# LevLine 4.0 — Selective Upset Gate Thesis

Status: **research-only / accuracy-primary / no production change**  
Date: **2026-09-12**

## Conclusion

A single fixed football/market weight is not the right abstraction for LevLine's winner-pick objective.

Historical evidence rejects the old production-like `75% PURE / 25% market` rule as a global winner selector: it changed the market side 131 times over the common 2022–2025 sample and lost those switches 56–75. PURE alone and simple football unanimity also failed as generic upset signals.

The rational next architecture is therefore **incumbent-preserving conditional reliance**:

1. start from the frozen T-120 F-ST winner;
2. preserve each football component separately rather than collapsing all football information into one PURE probability;
3. allow later information to challenge the incumbent only on disagreement games;
4. require corroboration from an information source that is plausibly orthogonal to the market/football disagreement;
5. grade the switch primarily by whether it increases straight-up winner accuracy.

This is a selective switch/gating problem, not a search for another universal 75/25-style blend.

## New historical finding: component resolution matters, but only near the boundary

A season-forward regularized stack using the market logit plus the four individual base-model logits (`logistic`, `extra_trees`, `xgboost`, `catboost`) scored 744/1,087 = 68.45% historically, versus 741/1,087 = 68.17% for the analogous aggregate-PURE F-ST architecture and 735/1,087 = 67.62% for the raw market.

The component-resolved stack beat aggregate F-ST only 10–7 on 17 disagreement games. Its week-block 95% interval includes no advantage, so this is not promotion evidence. The useful architectural implication is narrower: **do not discard disagreement structure among football submodels before the upset gate sees it.**

Like F-ST, this component-resolved stack did not learn to fade strong favorites. Its market disagreements remained concentrated near 50/50; the strongest market favorite it overturned was only about 55.1%.

## New historical finding: large score/margin disagreement is not independent upset evidence

The isolated margin-model forensics reject another tempting shortcut. Across all 1,087 historical games, the football score/margin model had roughly 9.96 points of absolute margin error versus roughly 9.49 for the market spread, a deficit of about 0.47 points.

The failure becomes more pronounced exactly where a naive upset gate might be tempted to trust the football model most. On the 73 games where the model margin and market spread differed by at least six points:

- the model's mean absolute margin error was about **2.03 points worse** than the market's;
- the week-block 95% interval for model-minus-market MAE was approximately **+0.13 to +3.68 points**, entirely on the wrong side of zero;
- the model was closer to the realized margin only about **35.6%** of the time;
- larger disagreement buckets generally produced larger model-minus-market error.

Therefore a large football-vs-market projected-margin gap is **diagnostic context only**. It cannot count as an independent corroborating channel for a clear-favorite override, and it cannot rescue football unanimity. Any future value from score structure must be demonstrated through a separately frozen hypothesis on prior data rather than inferred from raw disagreement magnitude.

## Super-team / reputation hypothesis

Peer-reviewed NFL evidence supports testing reputation anchoring. Fodor, Patterson & Shank (Economics Letters, 2025; DOI 10.1016/j.econlet.2025.112288) report that preseason Super Bowl expectations influence both betting behavior and sportsbook closing lines through the season.

That justifies storing preseason futures as a **reputation feature**. It does not justify a mechanical fade.

LevLine's historical data rejects the crude version:

- all four football components opposing the market: 38–58;
- same condition when the market favorite also had stronger preseason Super Bowl reputation: 21–29;
- same condition against a preseason top-eight favorite: 7–15.

Therefore `super_team=true` is diagnostic context, not an upset trigger.

## What an upset trigger actually needs

The evidence points toward **orthogonal contemporaneous corroboration**. Candidate feature families are:

### 1. Football disagreement structure

- each base-model probability and side;
- vote count against the incumbent;
- mean football-vs-market residual;
- cross-model dispersion;
- whether disagreement is broad or driven by one model.

A large score/margin disagreement is not a separate channel. Historical margin forensics show that treating it as one would double-count a weaker football view rather than add orthogonal evidence.

### 2. Market path and microstructure

- T-120 → T-60 → T-45 → T-30 consensus movement;
- fraction of books moving toward the challenger;
- cross-book dispersion and its contraction/expansion;
- quote freshness and source count.

A football underdog thesis is more credible when independent books are also moving toward that side while the consensus has not yet crossed 50%. This remains a hypothesis to test prospectively, not an authorized follow-the-move rule.

### 3. Authoritative player-state change

After source qualification, use only point-in-time information actually published before the horizon:

- QB availability;
- role-weighted inactive shock only after a separate player-value model is authorized;
- replacement burden only after a separate player-value model is authorized;
- expected-role uncertainty;
- time since official announcement.

The gate should ask whether the market has fully digested the news, not simply add an injury penalty twice. Until numeric player impacts are separately authorized, player state remains timestamped descriptive evidence only.

### 4. Travel/rest/circadian context

This is a legitimate general feature family, not a Rams-specific hindsight patch. NFL-inclusive sleep/circadian research has found travel-direction and time-zone associations with performance (Roy & Forest, Journal of Sleep Research, 2018; DOI 10.1111/jsr.12565), while newer football research continues to find travel-direction effects.

Prospective context can include:

- time zones crossed;
- direction of travel;
- local kickoff time relative to body-clock time;
- short-week/rest differential;
- international venue;
- verified arrival/acclimation information when timestamped and reproducibly sourced.

Generic rest differential is a descriptive control/modifier rather than a standalone edge: modern NFL-specific evidence does not establish a meaningful current bye or mini-bye advantage. Circadian/travel context likewise remains an interaction hypothesis, not a switch trigger.

No rule is authorized from the 2026 Rams–49ers result itself. That game may motivate source capture, but completed 2026 outcomes cannot define the thresholds.

### 5. Reputation / anchoring

- preseason Super Bowl implied probability/rank;
- preseason win-total expectation;
- reputation gap between favorite and underdog.

This is an interaction feature only. Historical evidence does not support using it alone.

## Prospective evidence architecture

The upset-gate monitor should preserve, rather than prematurely combine, the three strongest currently instrumented channels:

1. component-resolved football probabilities and disagreement structure;
2. strict-PIT market state and same-sportsbook movement microstructure at T-120/T-60/T-45/T-30;
3. timestamped qualified player-state observations and changes.

Those records must be composed with no completed 2026 outcome, no post-cutoff backfill, no switch threshold, no cross-channel evidence score, and no fitted conjunction. A future candidate may be specified only after prior evidence exists, with a new frozen candidate ID and a fresh evaluation period or genuinely prior training sample.

## Training and selection philosophy

The final winner objective is zero-one accuracy, but the gate should not be fitted by brute-force accuracy threshold search. Earlier LevLine work already showed that direct empirical hit-rate weight searches were unstable and underperformed.

Use regularized, classification-calibrated surrogate training only after a legally available prior sample exists, then select prospectively by:

- overall winner-accuracy delta versus frozen F-ST;
- challenger-only-correct vs incumbent-only-correct;
- disagreement rate;
- switch win rate;
- week-block uncertainty.

Brier/log loss/calibration remain secondary diagnostics and confidence-layer controls.

## Prospective stopping rule

No conditional subgroup gets promoted because it looks good after a few 2026 games. Any material switch logic requires:

- a frozen candidate ID;
- a declared feature set before its evaluation period;
- strict PIT inputs;
- no completed-2026 outcome tuning;
- same-game paired grading against F-ST;
- explicit authorization before production.

The highest-value immediate work is therefore to collect the orthogonal evidence correctly and evaluate whether it wins the *switches*, not to increase PURE's global weight.