# ATS Historical Key-Mass Challenger — Final Receipt

**State:** COMPLETE  
**Research branch:** `research/ats-historical-challenger-20260924`  
**Validated execution head:** `8dbe37008324c6d5d3a69116c897ee599b85e22a`  
**GitHub Actions run:** `36065686319` — SUCCESS  
**Evidence artifact:** `10836511323` / `ats-historical-keymass-36065686319`  
**Artifact digest:** `sha256:93b378de840de1ff8e6158f5c9df1da55a84ad3306ea1c695b1fb4537a5a9a59`

## What was tested

The accepted ATS Frontier V2 constant-scale Student-t key-mass distribution was held fixed. The experiment changed only the distribution location center:

1. `KMASS-MARKET` — accepted normalized market home-margin center.
2. `KMASS-LEVLINE` — leakage-safe reconstructed LevLine/F-ST coherent fair margin.
3. `KMASS-BLEND` — training-only blend of market and LevLine centers with market weight in `{0.0, 0.1, ..., 1.0}`.

The exact accepted V2 `CONSTANT_SCALE_KEY` nuisance fit for each outer season was reused verbatim. This made center choice the experimental variable rather than reopening the distribution search.

The official historical F-ST archive supports a clean center reconstruction beginning in 2021, so the valid outer-test set is 2022-2025. Earlier requested years were not fabricated or filled with a proxy. Completed 2026 outcomes were never loaded into fitting or scoring.

## Common-row coverage

The paired outer-test sample contains **1,087 games**:

- 2022: 271
- 2023: 272
- 2024: 272
- 2025: 272

All eligible target rows had the required historical market, total, F-ST and reconstructed-center values. The coverage gate passed.

## Primary result

Exact integer-margin log score; lower is better:

| Candidate | Score |
|---|---:|
| `KMASS-MARKET` | 3.8529284698 |
| `KMASS-LEVLINE` | 3.8520079145 |
| `KMASS-BLEND` | 3.8517646736 |

The market score exactly reproduces the accepted V2 `CONSTANT_SCALE_KEY` score, providing an important implementation check.

### LevLine vs market

Aggregate paired delta: **-0.0009205553**.  
10,000-resample paired season/week-block 95% interval: **[-0.0060945398, +0.0043082873]**.  
Bootstrap probability favorable: **0.6370**.  
Favorable outer seasons: **2 of 4**.

Season deltas:

- 2022: +0.0081312741
- 2023: +0.0035526595
- 2024: -0.0054673811
- 2025: -0.0098654949

### Blend vs market

Aggregate paired delta: **-0.0011637962**.  
10,000-resample paired season/week-block 95% interval: **[-0.0024836545, +0.0001601218]**.  
Bootstrap probability favorable: **0.9576**.  
Favorable outer seasons: **2 of 4**.

Season deltas:

- 2022: +0.0014263695
- 2023: +0.0000600322
- 2024: -0.0009450452
- 2025: -0.0051870187

Training-only selected market weights for the blend were 0.7, 0.8, 0.9 and 0.7 for the 2022-2025 outer folds respectively. The selected blend therefore remained strongly market-weighted.

## Supporting result: key mass remains real

The key-mass component remained materially favorable versus the same-center no-key ablation:

- Market center: -0.0827183918
- LevLine center: -0.0868224780
- Blend center: -0.0834522513

This independently reinforces the earlier V2 conclusion that the finite key-number mass adjustment is the robust mechanism. The new evidence does **not** establish that replacing the market location center with the reconstructed LevLine center is a stable additional improvement.

## ATS diagnostic

This is diagnostic only; it is not a historical betting-return claim.

- `KMASS-MARKET`: 540-518-29, 51.04% excluding pushes.
- `KMASS-LEVLINE`: 535-523-29, 50.57% excluding pushes.
- `KMASS-BLEND`: 543-515-29, 51.32% excluding pushes.

The primary decision remains based on proper scoring, not ATS hit rate.

## Preregistered disposition

**`RETAIN_KMASS_MARKET`**.

Both non-market centers produced tiny favorable aggregate primary-score deltas, but neither satisfied the frozen advancement gate:

- both bootstrap intervals cross zero;
- both improve only 2 of 4 outer seasons;
- coverage passed, but coverage alone cannot rescue the statistical/season-stability failures.

No threshold was relaxed after seeing the results, no post-hoc winner was promoted, and no production authorization was created.

## Evidence hashes

- `CENTER_ARCHIVE_RECEIPT.json`: `114d70f3a1c42ecf1a66c7fe0db3257d1df996fde2dcdfb9edcbf852dd8949c8`
- `OOF_PREDICTIONS_2022_2025.csv`: `94568856d2fdaea26b0ba1e04931f1101f8080b285792775565c95841b936e26`
- `RESULTS.json`: `60554e8c8db69a318f9cce3cdebab977ff36b4458ea058a458621a6bce5f69db`
- `TUNING_AND_BLEND_WEIGHTS.json`: `280834288aedb6f51f5ebeab18a73ee7848eba7c9e19a6f4a642a58edba596ab`

Machine-readable closeout: `research/ats-historical-challenger-result-registry.json`.

**Production changed:** NO.  
**Completed 2026 outcomes used:** 0.  
**Production authorization:** NONE.
