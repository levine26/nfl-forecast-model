# ATS Market Manifold V2 — Result Summary

Status: **COMPLETE — NO MATERIAL IMPROVEMENT**

Canonical scientific execution SHA: `3d1f8cc397cf3b16ac5c800ce214a9bb74110be6`  
Workflow run: `36082091556`  
Evidence commit: `848254eb18d944041c97a8cfcbe5d2d9b2fd2553`  
Outer OOF N: `1087` across 2022–2025  
Evidence class: `DEVELOPMENT_NON_PRISTINE`  
Completed-2026 outcomes used: `0`  
Production changed: `False`

## Result

The stronger market-only V1 null remains the winner.

| Candidate | Candidate − `KMASS-MARKETML-IPROJ` CPL log loss | 95% season+week block interval | Classification |
|---|---:|---:|---|
| `ATS-MM-SHAPETILT-V1` | +0.0014140085 | [+0.0000625252, +0.0027069726] | `NO_MATERIAL_IMPROVEMENT` |
| `ATS-MM-SHAPETILT-MEANFIX-V1` | +0.0005523346 | [-0.0001612205, +0.0012416276] | `NO_MATERIAL_IMPROVEMENT` |

Positive delta is worse. Neither candidate produced an implementation candidate.

## Chronology is the central diagnostic

The frozen prior-only selector chose:

- 2022: `theta = 0.75`, based only on 2021;
- 2023: `theta = 0.00`;
- 2024: `theta = 0.00`;
- 2025: `theta = 0.00`.

The 2022 target season falsified the 2021-favored shape transfer:

- unconstrained shape tilt: 2022 CPL delta `+0.0056716872` versus N1;
- N1-mean-preserving shape tilt: 2022 CPL delta `+0.0022154529` versus N1.

After 2022 became available to the prior-only training pool, theta=0 was optimal and both candidate families collapsed exactly to N1 for every later outer season. Consequently there were **zero favorable outer seasons** for either candidate.

This is not evidence that the optimizer failed to find a sufficiently aggressive weight. The frozen grid showed the opposite: after 2021, larger positive theta values became progressively worse as more history accumulated.

## ATS side-switch evidence

Relative to N1:

- unconstrained shape tilt switched 104 sides and went `47-54-3` on those switches (46.53% ex-push);
- N1-mean-preserving tilt switched 54 sides and went `25-27-2` (48.08% ex-push).

The unconstrained candidate also failed the material-calibration guard. The mean-preserving candidate passed calibration but still had a worse primary proper score and no favorable outer season.

## Scientific interpretation

PR #583 established that archived historical market-moneyline probability adds useful information to spread-only KMASS when used to set aggregate positive/negative margin mass.

V2 tested a stricter extension: whether the **moneyline residual relative to the KMASS spread-implied win probability** should also monotonically redistribute probability within those sign regions around the ATS boundary. On the frozen 2022–2025 development sample, the answer for this specific low-capacity mechanism is no.

The evidence now supports a narrower working model:

1. keep the sportsbook spread as the location anchor;
2. keep accepted constant scale and 0/±3/±7 key masses;
3. retain the market-moneyline sign-mass projection as the strongest validated market-only cross-market mechanism;
4. do **not** add this smooth residual-driven within-sign tilt;
5. do **not** reopen F-ST transfer, generic football features, center replacement, or conditional scale based on these results.

## What this closes

This result closes, for the current historical evidence base, the hypothesis that a single monotone smooth function of static spread–moneyline inconsistency should move mass across the ATS boundary after sign mass has already been calibrated to the moneyline.

It does not test richer **point-in-time market microstructure** such as same-book spread/moneyline movement, price path, cross-book dispersion, or time-aligned liquidity/price changes. Those require a separately sourced and preregistered historical market dataset; they must not be approximated from the opaque-horizon archive.

No production promotion is authorized.