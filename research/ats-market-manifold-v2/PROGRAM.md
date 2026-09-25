# LEVLINE ATS MARKET MANIFOLD V2

Status: PREREGISTERED / PRE-RESULT — RESEARCH ONLY

Base main SHA at program opening: `f80a1445ec62ca55e114c6d38c550c926697cd20`.

## Objective

Test whether the historical sportsbook moneyline contains **within-sign margin-shape information** that improves Cover/Push/Loss probabilities beyond the already-positive market-only `KMASS-MARKETML-IPROJ` null, while retaining the sportsbook spread as the location anchor and the accepted constant-scale 0/±3/±7 key-mass structure.

This program is a new experiment. It is not a rescue of ATS NextGen Q2/Q3, ATS Frontier M4, the historical center challenger, or ATS Cross-Market Transfer V1.

## Canonical prior evidence

1. ATS Frontier V2: the simple constant-scale key-mass model captured essentially the entire accepted margin-distribution gain; conditional scale added no incremental value.
2. PR #582: replacing the sportsbook center with LevLine/F-ST or a center blend did not clear the historical advancement gate. The market center is therefore frozen here.
3. PR #583 / ATS Cross-Market Transfer V1: imposing archived historical market-moneyline win mass on the spread-centered KMASS distribution improved CPL log loss from `0.7696147399` to `0.7682207714` on 1,087 chronology-clean 2022–2025 games. Adding F-ST's market-relative probability displacement did not improve any preregistered matched-null comparison.
4. ATS NextGen Q2 V1 was structurally invalid because its fixed finite support folded material tail mass into endpoints. V2 therefore uses adaptive support and never folds tails into endpoints.
5. ATS NextGen Q3 showed that adding compact football state to a market-only direct CPL hurdle did not improve proper scores. V2 therefore contains no football features in its primary candidate family.

## Core inference

The market-only improvement in PR #583 suggests that spread and moneyline are not redundant surfaces. V1 used the moneyline only to set total positive/negative margin mass. V2 asks whether the **residual disagreement between the moneyline and the KMASS spread-implied win probability** also indicates where probability should sit *within* the positive and negative margin regions.

Define, before target outcomes are inspected:

`r_ml = logit(p_market) - logit(p_KMASS_win)`

where `p_KMASS_win = P_q(M>0) / (P_q(M>0)+P_q(M<0))` from the frozen spread-centered KMASS distribution `q`.

V2 never uses `p_FST`, `pure_prob`, LevLine fair margin, football residuals, or completed-2026 outcomes in a primary candidate.

## Frozen candidate family

### Null N0 — `KMASS-MARKET`
Accepted spread-centered constant-scale key-mass distribution.

### Strong null N1 — `KMASS-MARKETML-IPROJ`
The exact market-only sign-mass information projection from PR #583. Tie mass is preserved, market conditional non-tie home-win probability determines total positive/negative mass, and within-sign relative mass is otherwise unchanged.

### Candidate A — `ATS-MM-SHAPETILT-V1`
Start from N1. On adaptive integer support, apply a bounded smooth ATS-boundary shape score

`h(m,L) = tanh((m-L)/3)`

where `L` is the repository-normalized expected home margin / ATS threshold used by the accepted KMASS contract. For game-level moneyline residual `r_ml` and frozen scalar transfer weight `theta`, reweight nonzero cells by

`exp(theta * r_ml * h(m,L))`

then renormalize **separately within M>0 and M<0** so market-moneyline sign masses and baseline tie mass remain exact. No other parameter changes.

### Candidate B — `ATS-MM-SHAPETILT-MEANFIX-V1`
Apply Candidate A's shape score while additionally preserving the baseline `KMASS-MARKET` expected margin through one numerical Lagrange multiplier on `m`. Market-moneyline sign masses and baseline tie mass remain exact. This candidate tests whether any shape gain survives when mean drift is prohibited.

## Frozen transfer-weight grid

`theta ∈ {0, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00}`.

For each outer target season, choose theta using only prior seasons and mean multinomial CPL log loss. Exact ties choose the smaller theta. `theta=0` must reproduce N1 exactly. Candidate B uses the same selected theta as Candidate A; it does not receive a separate tuning search.

No alternative temperature, tanh width, basis function, interaction, threshold, spread bucket, total-line rule, or nonlinear weight search is authorized after scoring begins.

## Chronology and evidence boundary

Outer scoring seasons are 2022, 2023, 2024, 2025 on the exact canonical common-row universe where possible. Each target season is scored once after prior-only weight selection. All nuisance fits used in inner validation must themselves be season-forward.

These seasons are **development / non-pristine evidence** because they have informed prior LevLine ATS research. A favorable V2 result may authorize a new prospective shadow identity; it is not independent confirmation and cannot directly authorize production.

Completed 2026 outcomes are forbidden from architecture design, fitting, weight selection, thresholding, calibration, scoring, or interpretation used to modify the candidate.

## Primary metric and advancement gate

Primary metric: mean multinomial Cover/Push/Loss log loss on exact paired rows.

Each candidate is compared to strong null N1. `IMPLEMENTATION_CANDIDATE` requires all of:

1. candidate-minus-N1 aggregate CPL log loss < 0;
2. deterministic 10,000-resample season-stratified NFL-week block-bootstrap 95% upper bound < 0;
3. favorable paired delta in at least 3 of 4 outer seasons;
4. no material calibration degradation (same intercept/slope tolerances as PR #583);
5. zero leakage/numerical failures and adaptive omitted tail mass below `1e-12` on every scored row;
6. at least 10 candidate-vs-N1 ATS side switches and no single-week concentration;
7. ex-push ATS hit rate not at least 1 percentage point worse than N1 when there are at least 10 switches;
8. reasonable implementation complexity.

If neither candidate clears the gate, classification is `NO_MATERIAL_IMPROVEMENT`. A favorable point estimate that fails uncertainty/stability gates may be `HISTORICALLY_PROMISING`, but may not be promoted.

No post-hoc slice, including the previously observed `|spread|<=2` pattern, may promote or redesign a V2 candidate.

## Production firewall

All work is isolated under `research/ats-market-manifold-v2/` plus dedicated research workflow(s). No production F-ST/Sunday Signal probability, fair spread, ATS pick, grading, history, deployment, or official output may change in this program.