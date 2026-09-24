# DISTRIBUTIONAL FORECASTING RESEARCH

## Scientific need

ATS decisions depend on the probability mass around a betting line, including exact push mass, not just expected final margin. Dmochowski's NFL betting decision theory is consistent with this distinction: the median can determine side, while additional quantiles/distribution information governs wager selectivity.

## Methods reviewed

### GAMLSS
Models location, scale and shape as functions of covariates. Attractive for small/medium samples because complexity is explicit and can be strongly regularized. Candidate families could include Student-t, generalized normal or skewed/heavy-tailed alternatives.

### NGBoost
Produces full conditional distributions through natural-gradient boosting. Flexible and open source, but game-level NFL sample size makes unrestricted tree complexity a concern. It is a tool to compare under frozen hyperparameters, not a default choice.

### Distributional forests
Can estimate heteroskedastic/skewed conditional distributions with nonlinear splits; weather post-processing literature provides strong methodology. Risk is high variance in small NFL strata.

### Bayesian distributional regression
Supports hierarchical partial pooling and coherent uncertainty. Computationally heavier but naturally compatible with M3 latent states.

### Quantile regression / forests
Useful as distribution diagnostics and for decision-relevant quantiles. ATS-Q1 already shows that quantile machinery alone does not create market-incremental information.

### Empirical / discrete conditional PMFs
Most directly compatible with NFL's integer/lattice scoring and pushes. Tail/support handling is the dominant numerical requirement after Q2 V1.

### Joint-score models
Bivariate score models capture home/away score dependence and can imply margin/total jointly. Soccer Poisson models are conceptual precedents, but NFL scoring increments and possession structure make direct Poisson transfer inappropriate.

## Evaluation principles

- Primary model selection uses strictly proper scores appropriate to the predictive object: log score, CRPS or preregistered discrete equivalents.
- Calibration and sharpness are reported separately.
- ATS hit rate cannot select a distribution in development.
- Push probability must be represented explicitly at whole-number spreads.
- Distribution tails must be numerically validated before target scoring.
- Any flexible distributional learner must be compared with a market-implied/null distribution on identical rows.

## Research conclusion

Distributional sophistication is valuable **only after information conditioning is correct**. Q1/Q3 prove that better loss functions/classes do not rescue weak inputs. M4 survives because Q2 never received a valid test and because exact lattice/push representation is scientifically necessary, but it is not granted a prior edge.