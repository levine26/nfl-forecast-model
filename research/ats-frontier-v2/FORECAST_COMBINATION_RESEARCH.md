# FORECAST COMBINATION RESEARCH

## Conclusion first

Forecast combination is **not** a Phase-1 Frontier candidate. It is a downstream operation that becomes scientifically justified only if two or more independently validated components contain complementary residual information.

## Why simple stacking is not the answer

Candidate 5 directly tested a historical residual stack and changed zero F-ST winners across 815 development games; every residual ablation also produced zero switches. This is unusually strong evidence that combining the existing LevLine information set through another layer is not a promising mechanism.

The general forecasting literature reinforces caution:

- Gneiting & Ranjan show that even distinct calibrated probability forecasts can become uncalibrated and insufficiently sharp under simple linear pooling, motivating recalibration such as beta-transformed pools.
- Claeskens et al. explain the forecast-combination puzzle: estimated “optimal” weights incur estimation error and can underperform simpler fixed/equal combinations.
- Combination benefits depend on diversity of errors, not model count.

## Future admissibility test

Combination research may reopen only after Phase 4 if at least two components satisfy all of:

1. individually non-inferior or better proper-score evidence versus their market null;
2. meaningfully imperfect residual correlation / demonstrable information diversity;
3. chronology-clean OOF forecasts for identical rows;
4. a small preregistered weight family or constrained combination rule;
5. recalibration evaluated under proper scoring;
6. no tuning to ATS hit rate or ROI.

## Methods retained for future consideration

- constrained stacking;
- linear pool + fixed recalibration;
- beta-transformed linear pool;
- Bayesian model averaging where model likelihoods/priors are defensible;
- ensemble model output statistics / distributional post-processing;
- dynamic weights only with a strongly justified state variable and enough sample.

## Methods rejected as default

- unrestricted stacking over many correlated LevLine models;
- winner-take-all model selection by recent ATS record;
- retrospective dynamic weight switching;
- adding a market forecast to a model already trained primarily to mimic the market and calling the result independent information.

Forecast combination remains a **conditional Phase-4/5 technique, not an information mechanism**.