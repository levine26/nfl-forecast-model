# Phase 4 parallel baseline-contract reconciliation

This is an **identity-only audit**, not a new model experiment or refit. It traces the difference between the season-forward F-ST architecture (741/1087 in the frozen 2022–2025 comparison) and the frozen final-coefficient reconstruction (740/1087); verifies their distinct Week 1–4 and Week 1–6 counts on **the same keyed rows**, and verifies three known ties are improperly credited as away wins under legacy `home_win=0`.

Run `PYTHONPATH=src:. python research/post_week4_phase4/reconcile_baselines.py --output /tmp/levline_phase4_baseline_receipt.json` or `pytest -q research/post_week4_phase4/test_reconcile_baselines.py`. The report is descriptive, with zero 2026 outcome use. No automatic refit or model tuning, no production mutations. A full compliant tie-excluded OOS redesign would need a distinct before-result contract, including a new equally retrained comparator; not allowed as a retroactive Phase 3 repair.

## Verified receipt — exact source-of-discrepancy findings

The [machine-readable frozen baseline receipt](evidence/baseline_identity_receipt.json) was executed successfully by [isolated audit workflow #37697977933](https://github.com/levine26/nfl-forecast-model/actions/runs/37697977933) from recovered/verified 1,615-game F-ST training artifacts. The same **1,087 keyed 2022–2025 games** yield:

| Comparison method | All-season winners | Weeks 1–4 | Weeks 1–6 | 2022 season |
|---|---:|---:|---:|---:|
| Season-forward F-ST architecture | 741 / 1,087 | 167 / 256 | 243 / 372 | 182 / 271 |
| Frozen final coefficients for 2026 | 740 / 1,087 | 164 / 256 | 241 / 372 | 181 / 271 |

**Resolution:** the older 164/241 early-week values used the *frozen-final-coefficient* F-ST comparator; the later 167/243 values used the strictly season-forward historical F-ST architecture. This is a **method/estimand distinction**, not evidence of corrupted picks or a reason to retune the model. All 2023–2025 per-season correct totals match between the two; only 2022 differs overall.

The same three established ties in 2022 and 2025 were incorrectly marked `home_win=0`/away-correct in both legacy scoring methods. Static non-refitted exclusion produces season-forward F-ST 738/1,084 and frozen final F-ST 737/1,084. These are **descriptive sensitivities only**: tied games may remain in earlier training folds. No tie-excluded OOS refit is claimed.

This audit does not touch F-ST/Sunday Signal production; it uses no completed 2026 outcome.
