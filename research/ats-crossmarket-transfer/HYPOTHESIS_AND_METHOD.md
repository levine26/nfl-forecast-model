# Hypothesis and Method

## Repository-motivated hypothesis

The canonical historical-center experiment retained the sportsbook-centered KMASS distribution: replacing or blending the spread-derived margin center with reconstructed LevLine/F-ST fair margins did not satisfy the frozen advancement gate. Separately, the chronology-clean F-ST winner stack has shown incremental historical winner-probability information relative to its archived market-moneyline input. This program therefore tests a narrower inference: preserve the sportsbook spread as the location of the discrete score-margin distribution, preserve the accepted 0/|3|/|7| key-mass shape, and inject only F-ST's market-relative winner-probability displacement through constrained probability reweighting.

This is a research hypothesis, not an established NFL betting fact.

## Information projection

For a baseline discrete margin PMF q and a constraint set C, an information projection chooses p in C minimizing KL divergence D_KL(p || q). Csiszar's I-divergence geometry formalizes minimum-discrimination-information projection onto convex sets and characterizes the resulting projected distributions. In this experiment the simple projection holds tie mass fixed, sets positive/negative total mass to match a target conditional home-win probability, and otherwise preserves within-sign relative mass exactly.

Reference: I. Csiszar (1975), *I-Divergence Geometry of Probability Distributions and Minimization Problems*, Annals of Probability 3(1), 146-158, DOI 10.1214/aop/1176996454.

## Exponential tilting and the mean-preserving projection

Adding a linear expected-margin constraint to a KL projection yields an exponential-family tilt of the baseline probabilities under the corresponding Lagrange multiplier. Here the sign totals are fixed by the target winner probability, tie mass is fixed, and one scalar exponential tilt is solved so that the projected expected margin equals the baseline KMASS expected margin. The numerical implementation uses an adaptive integer support and expands it until omitted baseline tail mass is below 1e-12; the tail is never folded into endpoints.

## Probability forecast combination

The transfer target uses

`logit(p_target) = logit(p_market) + alpha * (logit(p_FST) - logit(p_market))`.

This is a low-dimensional nonlinear forecast-combination/shrinkage construction. The broad literature on pooling probability distributions distinguishes linear and logarithmic aggregation and emphasizes that combination rules encode substantive assumptions; this program does not claim that the chosen transfer equation is generally optimal.

Reference: C. Genest and J. V. Zidek (1986), *Combining Probability Distributions: A Critique and an Annotated Bibliography*, Statistical Science 1(1), 114-135, DOI 10.1214/ss/1177013825.

## Proper scoring, calibration, and sharpness

Architecture selection uses multinomial cover/push/loss log loss rather than raw ATS win percentage. Log score and Brier-type scores are proper scoring rules, which reward calibrated probability distributions rather than thresholded classification alone. Calibration and sharpness are reported as diagnostics and are not used for post-hoc rescue.

References:

- T. Gneiting and A. E. Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*, JASA 102(477), 359-378, DOI 10.1198/016214506000001437.
- T. Gneiting, F. Balabdaoui, and A. E. Raftery (2007), *Probabilistic Forecasts, Calibration and Sharpness*, JRSS B 69, 243-268, DOI 10.1111/j.1467-9868.2007.00587.x.

## Sportsbook spread as margin-location information

The experiment treats the point spread as the frozen market location signal because that is the result of the repository's accepted historical challenger. External sports-betting literature is consistent with treating the point spread as a strong location/median benchmark, but does not establish that it is perfectly efficient. Dmochowski (2023), using more than 5,000 NFL games, reports that sportsbook point spreads explain a large share of the variation in empirical median margin; older NFL market-efficiency studies likewise generally treat spreads as highly informative market summaries while documenting that small inefficiencies can exist.

References:

- J. P. Dmochowski (2023), *A statistical theory of optimal decision-making in sports betting*, PLOS ONE 18(6):e0287601, DOI 10.1371/journal.pone.0287601.
- N. J. Lacey (1990), *An estimation of market efficiency in the NFL point spread betting market*, Applied Economics 22(1), 117-129, DOI 10.1080/00036849000000056.
- H. S. Stern (2008), *Point Spread and Odds Betting: Baseball, Basketball, and American Football*, Handbook of Sports and Lottery Markets, DOI 10.1016/B978-044450744-0.50014-7.

## Cross-market coherence

Moneyline and point spread are different functionals of an underlying score-margin distribution. A spread-centered PMF implies a home-win probability, while the moneyline supplies a separately priced win-event probability. The market-only information-projection null asks whether those two market surfaces contain useful complementary information before F-ST receives any credit. The F-ST candidates then differ from their structurally matched market null only through the market-relative F-ST displacement.

This specific NFL ATS use of constrained information projection is the novel application being tested here; the underlying KL-projection, exponential-tilting, forecast-combination, and proper-scoring methods are established statistical methodology.
