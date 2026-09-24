# UNCERTAINTY PROTOCOL

## Paired comparisons

All candidate-v-null effects use exact common rows and are expressed as:

`delta = candidate_score - null_score`.

For loss metrics, negative favors the candidate.

## Final resampling procedure

Use at least `10,000` bootstrap resamples for final Phase-4 evidence.

Resampling unit: NFL week blocks within season, preserving all games from a sampled week together and preserving candidate/null pairing. Seasons remain explicit strata so one dense season cannot dominate by construction.

For each metric report:

- paired mean/median effect as appropriate;
- 2.5th / 97.5th percentile interval;
- bootstrap probability `P(delta < 0)` for descriptive context;
- exact number of common game rows and week blocks.

## Per-season reporting

Report 2022, 2023, 2024 and 2025 separately in addition to pooled development evidence.

Concentration diagnostics must show:

- share of aggregate proper-score improvement contributed by each season;
- top-10 game contribution to total log-score difference;
- number of rows with candidate improvement versus deterioration;
- whether a result is dominated by a single week or event.

A candidate cannot be `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` if all improvement is concentrated in one season or fewer than 10 game rows.

## ATS uncertainty

ATS diagnostics use exact binomial confidence intervals on non-push forced picks and report pushes separately. For paired candidate/null winner-change analyses, report the exact switched-game count; do not convert one or two switches into a generalized edge claim.

## Calibration uncertainty

Calibration intercept/slope are fit only as diagnostics on frozen predictions. They do not feed corrected probabilities back into the candidate.

## Multiple comparisons

No family-wide p-value fishing is permitted. Only the preregistered primary candidate/null comparisons and named ablations are inferential. Secondary metrics are supportive/diagnostic.

## Missing rows

Report coverage and causes. Bootstrap only the common-row population; never impute a candidate prediction solely to enlarge the sample.