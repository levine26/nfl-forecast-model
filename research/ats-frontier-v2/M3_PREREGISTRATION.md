# M3 PREREGISTRATION

## Candidate identity

`FV2-HIST-M3-DSSM-01`

Status: `FROZEN__PHASE4_ELIGIBLE`.

## Scientific question

Can a compact chronology-safe hierarchical dynamic state estimate incremental football information **after conditioning on the sportsbook market**, where fixed rolling averages previously failed?

This candidate is not a standalone football spread model. The sportsbook market is the center of the prediction; M3 may only estimate a shrinkage correction around it.

## Historical era

- state warm-up / training history begins: 2010 regular season;
- outer development seasons: 2022, 2023, 2024, 2025;
- 2022–2025 are explicitly non-pristine development evidence;
- completed 2026 outcomes are prohibited;
- postseason games may update latent state after completion but are excluded from the primary regular-season evaluation population.

## Prediction timing

Historical market input is the nflverse schedule market field and remains explicitly:

`HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`.

M3 therefore makes **no claim** to a historical T-120/T-60 operational horizon. The football state itself is computed only from games completed before the target kickoff.

## Latent state architecture

Use a linear-Gaussian hierarchical dynamic state-space model with the smallest identifiable state vector:

- team offense state `O(team,t)`;
- team defense state `D(team,t)`;
- QB state `Q(qb,t)`.

Do **not** add separate pass/rush offense/defense latent dimensions in V1. Unit expansion is an unfrozen future version, not a Phase-4 option.

### State evolution

Within season, each state follows a random walk:

`state_t = state_(t-1) + epsilon_t`, `epsilon_t ~ Normal(0, q)`.

At season transition:

`state_new = lambda * state_previous + (1-lambda) * league_mean + transition_noise`.

Partial pooling shrinks low-information teams/QBs toward league mean. New/rare QBs begin at the league QB prior and update only from prior completed games.

## Observation layer

The observation vector is intentionally compact and derived from prior-game nflverse PBP only:

- offensive EPA/play;
- defensive EPA/play allowed;
- QB EPA/dropback;
- offensive success rate and defensive success rate allowed only as fixed secondary measurement channels, not a searched feature family.

Garbage-time/neutral filters may not be searched after results. The V1 primary measurement uses all eligible offensive plays under one fixed repository-consistent PBP filter; neutral-state summaries are diagnostic only.

## Exact market relationship

Let `M_market` be the home-team expected margin implied by the historical market sign contract. The candidate location is:

`mu = M_market + delta_football`

with:

`delta_football = beta_team * [(O_home - D_away) - (O_away - D_home)] + beta_qb * (Q_home - Q_away)`.

Both correction coefficients are ridge-shrunk toward zero. The market-alone null is exactly the same distributional translator with `delta_football = 0` on identical rows.

This formulation ensures M3 cannot claim success merely by predicting football reasonably well; it must improve a market-centered forecast.

## Hyperparameters

The only tunable structural values are frozen to the following compact grid:

- team process variance `q_team ∈ {0.04, 0.10, 0.25}` in standardized observation units;
- QB process variance `q_qb ∈ {0.10, 0.25, 0.50}`;
- season carryover `lambda ∈ {0.50, 0.75}`;
- ridge penalty for market correction coefficients `alpha ∈ {10, 100}`.

Within-season persistence is fixed at `1.0`; no changepoint search is allowed in V1.

The grid is selected only by the nested chronological inner procedure in `CHRONOLOGY_CONTRACT.md`; no target-season outcomes may influence a hyperparameter before their prediction time.

## Predictive distribution

For M3 evaluation alone, use a market-centered Normal residual translator with scale estimated from prior-only market residuals. Candidate and null share the same scale procedure; only the M3 location correction differs.

The integer cover/push/loss probabilities are obtained by integer-bin integration. M3 does not inherit M4's Student-t/key-mass enhancements during its primary test, preventing representation changes from confounding the M3 mechanism.

## Primary metric

Paired multinomial cover/push/loss log loss versus the market-only null on exact common rows.

## Secondary metrics

- Brier score;
- CRPS of the margin distribution;
- calibration intercept/slope;
- reliability/resolution;
- margin MAE/RMSE;
- ATS hit rate only as a diagnostic.

## Preregistered ablations

1. `MARKET_ONLY` — null;
2. `STATIC_FOOTBALL_STATE` — prior-only exponentially pooled/static football summaries with no dynamic process noise;
3. `DYNAMIC_NO_QB` — O/D states only;
4. `DYNAMIC_FULL` — O/D + Q, the candidate.

No additional feature-family ablation may be created after target results are seen.

## Failure condition

M3 does not establish incremental information if `DYNAMIC_FULL` fails to improve paired primary proper score versus `MARKET_ONLY`, or if any apparent gain is reproduced by `STATIC_FOOTBALL_STATE` with no evidence that the dynamic representation contributes.

A noisy positive ATS result cannot rescue a proper-score failure.

## Production firewall

This candidate is research-only and cannot alter `F-ST-01-FROZEN-2026`, Sunday Signal, grading, history or deployment.