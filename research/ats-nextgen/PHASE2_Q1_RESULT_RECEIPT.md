# ATS Next-Generation — Phase 2 Stage A / Q1 Result Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** A — Q1  
**Candidate:** `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`  
**Classification:** **VALID NEGATIVE INCREMENTAL RESULT**  
**Result head:** `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`  
**PR:** #560  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** 0

## 1. Valid execution boundary

The first accepted Q1 historical evidence is GitHub Actions run `35920622523` (#7) on exact head `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`.

All controlling checks succeeded on that exact head:

- Q1 pre-result contract: **SUCCESS**;
- Q1 chronology-clean 2022–2025 OOF: **SUCCESS**;
- protected production-surface diff check: **SUCCESS**;
- immutable evidence upload: **SUCCESS**;
- LevLine research firewall `35920622410`: **SUCCESS**;
- ATS Phase-2 opening gate `35920622392`: **SUCCESS**;
- LevLine research validation `35920622570`: **SUCCESS**;
- Daily NFL model refresh / full pytest and regenerated-output validation `35920622374`: **SUCCESS**.

The Q1 runner regenerated the frozen 2015–2025 opening gate and matched canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d` before fitting.

The accepted evidence artifact is:

- artifact ID `10776898518`;
- artifact name `ats-nextgen-q1-35920622523`;
- artifact digest `sha256:b544a4928a3e2ab80861b7b3fcf581a6b51355961b80aa05ddc5e4a0554d0c36`;
- 1,087 chronology-clean outer-OOF rows from seasons 2022–2025.

## 2. Primary preregistered result

Q1 asked whether compact football state adds incremental quantile information beyond the market-only quantile comparator M2.

It does **not** under the frozen Stage-A evidence.

Overall 2022–2025 OOF:

| Quantile | M2 pinball | Q1 pinball | Q1 - M2 | M2 coverage error | Q1 coverage error |
|---|---:|---:|---:|---:|---:|
| 10/21 | 4.736212 | 4.736212 | 0.000000 | -0.009769 | -0.009769 |
| 1/2 | 4.749754 | 4.753243 | +0.003489 | -0.011500 | -0.013339 |
| 11/21 | 4.763994 | 4.760897 | -0.003096 | -0.012310 | -0.010470 |

Mean pinball across the three frozen quantiles:

- M2: `4.749986`;
- Q1: `4.750117`;
- Q1 minus M2: `+0.000131` (worse, not better).

The raw-line M0 comparator is also stronger overall on this aggregate (`4.747240`).

Therefore Q1 fails the preregistered incremental criterion in `Q1_QUANTILE_PREREGISTRATION.md`: it does not improve the primary pinball/calibration evidence relative to the market-only null.

## 3. Season stability

Mean pinball across the frozen quantiles, Q1 minus M2:

- 2022: `-0.004140` (Q1 better);
- 2023: `0.000000` (equal);
- 2024: `+0.003698` (Q1 worse);
- 2025: `+0.000950` (Q1 worse).

The result is not a stable season-over-season incremental gain.

## 4. Secondary diagnostics

Overall median/location metrics:

- residual/margin MAE: M0 `9.494480`, M2 `9.499508`, Q1 `9.506485`;
- residual/margin RMSE: M0 `12.360286`, M2 `12.382016`, Q1 `12.390468`;
- median absolute residual error is `7.5` for all three arms.

Quantile crossing is diagnostic only and is not repaired:

- M2: 87 / 1,087 rows (`8.0037%`);
- Q1: 79 / 1,087 rows (`7.2677%`).

Across the 42 preregistered fixed slice × quantile cells, Q1 pinball is better than M2 in 12, equal in 14, and worse in 16. Absolute calibration error is better in 3, equal in 32, and worse in 7. Favorable slices do not rescue the failed overall quantile evidence.

## 5. Model-behavior evidence

All expected inner rolling-origin target seasons were used; no inner target was omitted for insufficient rows.

The additional football-state features were frequently shrunk away or produced no change:

- Q1 and M2 low-quantile predictions are identical for all 1,087 rows;
- median predictions are identical on approximately 49.95% of rows;
- high-quantile predictions are identical on approximately 75.07% of rows.

This is consistent with the primary result: the frozen compact football-state block did not provide reliable incremental conditional-quantile information beyond the market-only model.

## 6. Evidence file identities

- `q1_outer_oof_2022_2025.csv` — SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- `q1_inner_alpha_selections.csv` — SHA-256 `22f9c1f12a359e3861c72c0f6d6f5839356b959944dc187fbaf68574b2f4fe45`;
- `q1_quantile_metrics.csv` — SHA-256 `0e79c2d5fbf435e8b5a231b056011b7e3b3fce2b3c3bf0edc9d8306af837ce23`;
- `q1_quantile_crossings.csv` — SHA-256 `b28bf439afb59f450d5a660dbd657c2802aa22fb10743bf3d1beaa695f724ef9`;
- `q1_fixed_slice_metrics.csv` — SHA-256 `c637ee936e5c8f29aa06c41aa8552aaeff66217f2c4f342b8cf64617a542c1ee`;
- `q1_summary.json` — SHA-256 `ae4eb4e35b99b05263cf806d9b9f8b6b9c32264217a3a8b83287687e938c31ad`.

## 7. Scientific disposition

Q1 V1 is **not incremental** and may not be rescued by:

- a different learner;
- a new quantile grid;
- a new alpha grid or tie-break;
- new football/player/weather/news/market features;
- post-hoc quantile repair/calibration;
- favorable ATS hit rate, ROI, or selected slices.

The negative result is preserved as evidence.

Stage B / Q2 may proceed exactly as preregistered. Q2 may consume only the frozen chronology-clean Q1 median residual interface from this Stage-A execution; doing so does not reclassify Q1 as a successful incremental candidate. Q2 remains a separate test of discrete NFL margin-distribution structure and probability calibration.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
