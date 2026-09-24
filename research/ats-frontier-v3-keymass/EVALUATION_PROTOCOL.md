# Evaluation Protocol

Formal confirmatory scoring is prohibited until the preregistered evidence threshold is met and the 2027 regular season has ended.

Primary: on exact common eligible rows, integer-margin log score for observed exact margin. Define paired delta = candidate loss - null loss; lower than zero is favorable.

Secondary: ranked probability score/CRPS, cover-push-loss log loss, multiclass Brier, calibration/reliability, key-number probability calibration, push calibration, and tail diagnostics. ATS hit rate is descriptive only. Economic diagnostics may record genuine same-horizon prices, no-vig estimates, candidate EV, and eventual ATS outcome, but cannot select or promote the model.

Final classification: `ELIGIBLE_FOR_PRODUCTION_REVIEW` only if all minimum-data rules hold, mean primary delta < 0, paired week-block 95% bootstrap upper bound < 0, each adequately sampled season has negative mean delta, and every leave-one-week-out pooled mean remains < 0. `REJECTED` if mean primary delta >= 0 after minimum evidence. Otherwise `INCONCLUSIVE`. No automatic production promotion.