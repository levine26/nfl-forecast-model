# LEVLINE ATS CROSS-MARKET INFORMATION TRANSFER V1

Status: EXECUTION AUTHORIZED — RESEARCH ONLY

## Objective

Test whether chronology-clean LevLine/F-ST market-relative winner-probability information improves ATS Cover/Push/Loss probabilities when the accepted sportsbook-centered constant-scale key-mass margin distribution is left in place.

This program does **not** reopen margin-center replacement. The sportsbook spread center is frozen. The only LevLine signal authorized for the primary challenger family is

`delta_FST = logit(p_FST) - logit(p_market)`.

## Canonical predecessor

PR #582 is merged. Its accepted disposition is `RETAIN_KMASS_MARKET`. The canonical predecessor established that changing the KMASS location to LevLine or a market/LevLine center blend did not pass the frozen advancement gate. This program therefore changes probability mass, not the sportsbook location parameter.

## Frozen candidates

1. `KMASS-MARKETML-IPROJ` — market-only sign-mass KL projection.
2. `ATS-XM-IPROJ-FST-V1` — same projection using a prior-only selected shrinkage weight on `delta_FST`.
3. `ATS-XM-IPROJ-FST-ALPHA1` — fixed full-FST displacement ablation.
4. `KMASS-MARKETML-MEANFIX` — market-only sign constraint plus baseline-KMASS mean constraint.
5. `ATS-XM-IPROJ-MEANFIX-V1` — same mean-preserving projection with the alpha selected for candidate 2.
6. `ATS-XM-CPL-OFFSET-V1` — direct conditional-cover logit offset using only `delta_FST`, with structural push probability preserved.

## Historical outer evaluation

Frozen target seasons: 2022, 2023, 2024, 2025.

For target season S:

- the historical F-ST stack is refit only on frozen archive rows with season < S;
- alpha/beta selection uses only candidate rows with season < S;
- the target season is scored exactly once;
- no random K-fold is permitted;
- completed-2026 outcomes are never loaded.

## Primary scientific target

Mean multinomial Cover/Push/Loss log loss on exact paired common rows. Every F-ST challenger is compared to its strongest structurally matched market-only null.

## Production firewall

This branch may add only isolated research code, workflow, documentation, machine-readable results, and receipts. It may not modify `F-ST-01-FROZEN-2026`, Sunday Signal forecasts, official ML probabilities, fair spreads, ATS picks, grading, public history, or deployment behavior.
