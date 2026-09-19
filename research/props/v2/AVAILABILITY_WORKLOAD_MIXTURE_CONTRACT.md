# Props 2.0 Availability / Workload Mixture Research Contract

Status: **PREREGISTERED MECHANISM STUDY — NOT A PROP MODEL**  
Candidate: `P2-AVAIL-MIX`  
Version: `levline-props-v2-availability-mixture-v0.1.0`

## Question

Does the historical point-in-time injury-report + offensive-snap record support a defensible
workload mixture that distinguishes:

- OUT
- ACTIVE_LIMITED
- ACTIVE_NORMAL
- ACTIVE_ELEVATED

without equating P(active) with P(normal workload)?

## Inputs

2021–2025 regular-season injury reports and offensive snap counts with stable player IDs.

Historical injury rows are eligible only when:
- a timezone-aware `date_modified` exists;
- the report timestamp is strictly before that team/week kickoff;
- the latest eligible pregame report is selected;
- the team/week has snap-source coverage.

If these timestamp requirements materially collapse the sample, the lane is frozen for prospective
2026 capture rather than silently using unqualified reports.

## Workload target

For each injured player/week:

```
current offensive snap share / median(last up to 4 prior active snap shares)
```

At least two prior active games are required. Target-week snap share is an outcome of this mechanism
study only; it is never a feature for the target week.

OUT is zero offensive snaps on a team/week with verified snap-source coverage.

Among active rows, a fixed 3-component Gaussian mixture is fit to log workload ratio. Components are
ordered by mean and named LIMITED, NORMAL, ELEVATED. There is no prop-outcome-driven component count,
threshold, or hyperparameter search.

Designation/position conditional state probabilities use Dirichlet(1) smoothing.

## Diagnostic gate before simulator integration

The historical mixture is considered usable enough for a later simulation challenger only if:
- at least 300 active qualified observations exist;
- every active mixture component has at least 5% weight;
- component medians are ordered LIMITED < NORMAL < ELEVATED;
- source audit shows no completed 2026 outcomes and no post-kickoff injury rows.

Passing this gate does **not** prove forecast improvement. It only authorizes a separate frozen
simulation experiment.

## Governance

No sportsbook information or prop outcomes enter this study. No completed 2026 workload outcomes
enter the fit. If later integrated, the mixture must receive a new candidate version and a paired
V1 evaluation contract.
