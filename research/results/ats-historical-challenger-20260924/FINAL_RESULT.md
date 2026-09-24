# LevLine ATS Historical Key-Mass Center Challenger — Final Result

Status: **COMPLETE**  
Accepted execution: GitHub Actions run `36065686319` at head `8dbe37008324c6d5d3a69116c897ee599b85e22a`  
Immutable evidence artifact: `10836511323` (`ats-historical-keymass-36065686319`)  
Artifact digest: `sha256:93b378de840de1ff8e6158f5c9df1da55a84ad3306ea1c695b1fb4537a5a9a59`  
Production firewall: **PASS** — production changed `false`; completed-2026 outcomes used `0`.

## Result

The preregistered disposition is **RETAIN_KMASS_MARKET**.

All three candidates were scored on the same 1,087 regular-season games: 271 in 2022 and 272 in each of 2023–2025. The historical F-ST/schedule join had zero missing rows and zero required-value removals in every archived season from 2021–2025.

| Candidate | Integer log score | Delta vs KMASS-MARKET | 95% blocked-bootstrap CI vs market | Favorable seasons | Center MAE | ATS W-L-P* |
|---|---:|---:|---:|---:|---:|---:|
| KMASS-MARKET | 3.852928470 | — | — | — | 9.4945 | 540-518-29 |
| KMASS-LEVLINE | 3.852007914 | -0.000920555 | [-0.006094540, +0.004308287] | 2/4 | 9.5906 | 535-523-29 |
| KMASS-BLEND | **3.851764674** | **-0.001163796** | **[-0.002483655, +0.000160122]** | 2/4 | 9.5065 | 543-515-29 |

\*ATS is a full-slate diagnostic at reference -110, not a claim of realized historical betting ROI.

The blend has the lowest aggregate integer log score, but it does **not** pass the preregistered advancement gate: its bootstrap interval crosses zero and it is favorable against market in only 2 of 4 seasons. Pure LevLine fails those same two gates. Coverage passes for both candidates.

## Season behavior

`KMASS-LEVLINE - KMASS-MARKET` primary deltas: 2022 `+0.008131274`, 2023 `+0.003552659`, 2024 `-0.005467381`, 2025 `-0.009865495`.

`KMASS-BLEND - KMASS-MARKET` primary deltas: 2022 `+0.001426370`, 2023 `+0.000060032`, 2024 `-0.000945045`, 2025 `-0.005187019`.

The training-only selected market weights for `KMASS-BLEND` were: 2022 `0.7`, 2023 `0.8`, 2024 `0.9`, 2025 `0.7`. These were chosen only from rows preceding each target season.

## Interpretation

The experiment does **not** support replacing the market center with the reconstructed LevLine/F-ST fair-margin center under the accepted constant-scale key-mass distribution. The aggregate improvements are too small and not stable enough across seasons to satisfy the frozen evidentiary standard.

The key-mass mechanism itself remains strongly supported. `KMASS-MARKET` retains a key-minus-no-key integer-log-score improvement of `-0.082718392`, reproducing the accepted V2 constant-key effect on the same 1,087 rows. The center experiment therefore isolates the negative result cleanly: the failure is not the discrete key-mass correction; it is the attempted center substitution/blend under this architecture.

## Next state

Do not alter production F-ST or Sunday Signal from this result. Close this center-only historical challenger as negative under its preregistered gate. Any next ATS challenger should preserve the validated constant-scale key-mass distribution while testing a genuinely new, preregistered source of incremental information rather than post-hoc retuning these three centers.
