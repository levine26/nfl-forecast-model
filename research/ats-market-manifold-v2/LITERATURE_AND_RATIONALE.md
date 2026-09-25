# ATS Market Manifold V2 — Literature and Rationale

## Why this experiment exists

The repository now contains a repeated empirical pattern:

- sportsbook spread is a very strong location anchor;
- explicit discrete NFL key-number mass materially improves the margin distribution;
- replacing the spread center with football-model output has not validated;
- adding football state directly to ATS probabilities has not validated;
- but ATS Cross-Market Transfer V1 found that archived historical **market-moneyline** probability improves the accepted spread-centered KMASS CPL score.

V2 therefore asks a narrower question: after the moneyline has fixed overall win/loss sign mass, does the **spread-versus-moneyline residual** contain information about the *shape* of the margin distribution within each sign region?

## Cross-market information

Fodor, Krieger, Kirch, and Kreutzer (2012), *Informational Differences in NFL Point Spread and Moneyline Markets*, directly study whether the moneyline contains information not fully represented by the point spread. Their same-spread comparisons report that moneyline ranking can distinguish cover outcomes among favorites. V2 does not assume their historical betting rule persists or is profitable in this repository's sample; it uses the paper only as prior motivation for testing nonredundancy between the two market surfaces.

Reference: A. Fodor, K. Krieger, D. Kirch, A. Kreutzer (2012), SSRN 2047243, DOI 10.2139/ssrn.2047243.

The repository's V1 result is stronger motivation for this specific program because it is exact-row and architecture-matched: `KMASS-MARKETML-IPROJ` improved CPL log loss relative to spread-only `KMASS-MARKET`, while subsequent F-ST displacement did not.

## Distribution rather than point prediction

Dmochowski (2023) frames sports wagering decisions in terms of the outcome distribution and its quantiles. In an empirical NFL analysis of more than 5,000 regular-season games from 2002–2022, sportsbook spreads explained a large share of variation in empirical median margin. The paper also emphasizes that additional quantiles beyond the median are required for optimal wager selection under pricing/commission. That is consistent with V2's design choice to leave the sportsbook location anchor intact and use remaining degrees of freedom on distributional shape rather than another point-margin predictor.

Reference: J. P. Dmochowski (2023), *A statistical theory of optimal decision-making in sports betting*, PLOS ONE 18(6):e0287601, DOI 10.1371/journal.pone.0287601.

## Distributional regression principle

Generalized distributional regression methods separate location, scale, and shape parameters rather than assuming all predictive information must move the conditional mean. Rigby and Stasinopoulos (2005) formalized generalized additive models for location, scale, and shape (GAMLSS). V2 uses the conceptual separation, not the GAMLSS software/model family: location and scale are deliberately frozen by repository evidence, and only a one-dimensional shape deformation is tested.

Reference: R. A. Rigby and D. M. Stasinopoulos (2005), *Generalized additive models for location, scale and shape*, JRSS C 54(3), 507–554, DOI 10.1111/j.1467-9876.2005.00510.x.

## Information projection / exponential tilting

The V1 market-moneyline null is a minimum-discrimination-style sign-mass projection: alter the baseline distribution only enough to satisfy a market win-probability constraint. V2 retains those exact sign constraints and adds a low-dimensional exponential tilt inside sign regions. This is an exponential-family deformation of the existing distribution, with Candidate B adding an explicit expected-margin constraint.

The purpose is not to claim the proposed basis is theoretically optimal. The basis is frozen because it is smooth, bounded, monotone across the ATS boundary, and low capacity. A positive result would establish historical evidence for this *specific* market-shape transfer, not for arbitrary nonlinear distributional modeling.

Reference: I. Csiszar (1975), *I-Divergence Geometry of Probability Distributions and Minimization Problems*, Annals of Probability 3(1), 146–158, DOI 10.1214/aop/1176996454.

## Why no conditional scale search

ATS Frontier V2 already tested conditional scale inside its preregistered margin-distribution family. The accepted Phase-4 evidence showed that the simpler `CONSTANT_SCALE_KEY` ablation reproduced essentially all of the full model's gain and conditional scale added no incremental value. Reopening scale after observing that result would be redundant research rather than a new hypothesis.

## Why no F-ST / football feature in the primary candidate

Two separate repository programs now constrain this choice:

- ATS NextGen Q3: compact football state did not improve the market-only direct CPL null on primary proper scores.
- ATS Cross-Market Transfer V1: F-ST had slightly higher winner accuracy than archived market ML on the 1,087 exact rows, but worse Brier/log loss; all three F-ST-to-ATS transfer mechanisms failed their matched-null gates.

V2 therefore treats market prices as the only primary predictive inputs. Football-model information can be reconsidered only in a separately preregistered future experiment with a genuinely new mechanism.

## Why the post-hoc boundary-local V1 slice is not a V2 gate

V1 descriptively found favorable F-ST transfer point estimates near `|spread| <= 2`, including a favorable joint `|delta_FST|`/spread cell. Those observations were seen after scoring and are therefore not eligible to define a historical V2 selection rule. V2 scores the full common slate. The old boundary slices may be reported again as descriptive diagnostics only.

## Falsifiable prediction

If moneyline residual information is useful only for total win/loss sign mass, Candidate A/B should not beat `KMASS-MARKETML-IPROJ`.

If the moneyline contains additional shape information conditional on the spread, a low-capacity within-sign tilt should improve CPL proper score on exact paired rows without relying on football features, spread-bucket cherry-picking, or target-season tuning.

Candidate B is the stricter falsification: if only Candidate A improves while mean-fixed Candidate B does not, the evidence would suggest the apparent gain depends on shifting the implied mean rather than on pure higher-order shape.