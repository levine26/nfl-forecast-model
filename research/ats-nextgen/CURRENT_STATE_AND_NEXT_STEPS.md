# Current State and Next Steps

## Current scientific state

The completed Spread & Points Next-Generation program established that LevLine should not attempt to beat the NFL spread market by simply improving unconditional mean-margin prediction or stacking another generic historical market residual model.

The current ATS program therefore changes the estimand, not the narrative around the old estimand.

The market remains the primary null. The research question is whether compact PIT-safe state improves:

1. conditional market-relative margin quantiles;
2. the shape of the discrete NFL margin distribution, including push/key-number mass and conditional scale;
3. direct cover/push/loss probabilities.

## What Phase 1 changed

Phase 1 froze exactly three experiments, one chronology, one sign convention, one evidence boundary, the proper-score selection rules, the Q2/Q3 blend grid, market nulls, selective-evaluation subsets, economics, key-number buckets, uncertainty requirements, and a leakage red-team contract.

It also established that historical spread-side juice/book/timestamp data are not present in the default nflverse schedule path. The Odds API can provide those fields historically from 2020 but historical access is paid. Therefore historical development without verified price will report probability quality and standardized-price sensitivity rather than pretend to have observed juice.

## Most important exclusions

The following are excluded before any Q1/Q2/Q3 result is seen:

- another generic mean residual stack;
- unrestricted gradient-boosting/model-family tournaments;
- finite-mixture margin models in V1;
- post-result feature additions;
- large historical player-state reconstruction;
- historical line-movement/book-dispersion features without auditable timestamps;
- conformal methods as a primary betting-probability head;
- retrospective completed-2026 outcomes;
- historical ROI threshold search.

Conformalized/distributional methods remain scientifically useful for future uncertainty diagnostics but are not a fourth Phase-2 primary experiment.

## Exact next action after Phase 1 closes

Phase 2 begins by creating a **research-only implementation branch** and implementing the shared data/chronology/grading test harness before any candidate fit:

1. materialize the 2015–2025 eligible regular-season dataset with provenance and market-source labels;
2. implement and pass synthetic sign/ATS grading tests;
3. implement the 2015 floor, inner rolling folds and outer 2022–2025 fold registry;
4. implement M0/M1/M2 baselines;
5. only then implement Q1, followed by Q2, followed by Q3 and the frozen blend protocol;
6. execute outer development only after implementation contracts and tests are committed.

Phase 2 must not reinterpret the merged Phase-1 contract because of observed results.