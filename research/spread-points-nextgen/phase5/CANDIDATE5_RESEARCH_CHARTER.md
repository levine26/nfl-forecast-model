# Candidate 5 Research Charter

**Candidate:** `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`  
**Phase:** 5 — Historical F-ST-Anchored Winner Integration  
**Status:** PREREGISTERED / RESEARCH ONLY  
**Branch base:** `d9302207c3dd0a82c89fadd2cd5adc52f6541bd0`

## Question
Can chronology-clean A0/B0 football representations identify a selective subset of frozen F-ST winner errors while preserving probability quality?

## Binding architecture
`logit(P_C5) = logit(P_FST) + X beta`, with the F-ST logit coefficient fixed at 1 and `beta` strongly L2-shrunk toward zero. Candidate 5 is not a replacement football model, weekly refit, hand-written gate, raw-EPA rebuild, or unrestricted learner tournament.

## Scope
The primary historical development/evaluation surface is exact-paired 2022–2024 OOF evidence. A0 and B0 are permitted as compact underlying representations despite their negative standalone Phase 4 results. C0 is excluded from the primary conclusion and may enter only the separately labeled market-aware diagnostic. D remains `ENSEMBLE_NOT_ELIGIBLE`.

No nonlinear learner is authorized in V1. No XGBoost, CatBoost, random forest, neural network, feature tournament, threshold search, or post-result rescue is authorized.

## Firewalls
- completed-2026 outcomes: prohibited from design, fitting, tuning, evaluation, rescue, and candidate survival;
- production `F-ST-01-FROZEN-2026`: immutable;
- Sunday Signal behavior and official forecasts: immutable;
- 2025: not pristine for Candidate 5; governed separately by the frozen diagnostic rule;
- winner threshold: strict `P > 0.5`; no tuning.

## Exit classification
Exactly one final state is allowed: `REJECTED`, `INCONCLUSIVE_BUT_COHERENT`, or `ELIGIBLE_FOR_PROSPECTIVE_PHASE6_SHADOW_VALIDATION`. Historical eligibility never authorizes production promotion.
