# Candidate 5 Model Specification

## Primary learner
Strongly regularized logistic residual/offset model:

`eta_i = logit(FST_i) + z_i' beta`

`P_i = sigmoid(eta_i)`

The F-ST offset coefficient is fixed at 1. There is **no free residual intercept** in V1; learned component corrections are centered through training-only scaling and shrink toward zero. This avoids turning Candidate 5 into an unconstrained recalibration layer.

## Objective
Minimize training mean Bernoulli log loss plus `0.5 * lambda * ||beta||_2^2` using deterministic SciPy L-BFGS-B.

Fixed regularization grid: `[0.1, 1.0, 10.0, 100.0]`.  
Default when tuning history is unavailable: `100.0`.  
Tuning metric: pooled chronology-clean log loss.  
Tie tolerance: `1e-4`; choose larger lambda when tied.  
Probability clipping for logit/log-loss arithmetic: `1e-6`.  
Winner rule: strict `P > 0.5`.  
No classification-threshold optimization.

Solver maximum iterations: 5,000; gradient supplied analytically; convergence failure is recorded and that target/arm fails closed to F-ST rather than changing the model family.

No calibration transform is applied to Candidate 5 after fitting. Calibration is diagnostic only.

## Bounded family
No nonlinear Candidate 5 learner is authorized in V1 because the live master plan contains no pre-result authorization that compels one. A null result is valid and cannot activate a rescue learner.
