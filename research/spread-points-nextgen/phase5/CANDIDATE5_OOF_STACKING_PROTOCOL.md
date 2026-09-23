# Candidate 5 OOF Stacking Protocol

The base A0/B0/C0 features for each target game are already OOF. The Candidate 5 meta-model is also strictly earlier-season trained.

## 2022–2024 development chronology
- **2022 target:** deterministic F-ST fallback / zero residual correction; no earlier Candidate 5 component meta-training surface exists.
- **2023 target:** fit each arm on 2022 only. No eligible prior meta-validation season exists, so use frozen default `lambda=100.0`.
- **2024 target:** choose lambda using 2023 only: for each lambda, fit on 2022 and score 2023 by log loss; deterministic tie-break favors stronger regularization. Refit selected lambda on 2022–2023 and score 2024.

Minimum fit size is 250 rows with both outcome classes. If not met, target rows fall back to frozen F-ST / zero correction. No future season may repair an earlier target.

## Frozen 2025 non-pristine diagnostic chronology
After the full contract is immutable, select lambda from the fixed grid using pooled chronology-clean validation predictions for 2023 and 2024 only:
- 2023 validation: fit 2022;
- 2024 validation: fit 2022–2023.
Select lowest pooled log loss; ties within `1e-4` choose the larger lambda. Refit on all 2022–2024 rows and score 2025 once. 2025 outcomes do not enter selection or fitting.

## Scaling
For every fit, feature mean and population standard deviation are learned on training rows only. Zero/non-finite training standard deviation maps that standardized feature to zero. Target rows use only the stored training transform.

## Required audit ledger
Every prediction stores target season/week, training seasons, tuning seasons, selected lambda, fallback status, source candidate IDs/hashes and Candidate 5 code/config identity. Tests must fail if any training season is >= target season.
