# Phase 4 parallel baseline-contract reconciliation

This is an **identity-only audit**, not a new model experiment or refit. It traces the difference between the season-forward F-ST architecture (741/1087 in the frozen 2022–2025 comparison) and the frozen final-coefficient reconstruction (740/1087); verifies their distinct Week 1–4 and Week 1–6 counts on **the same keyed rows**, and verifies three known ties are improperly credited as away wins under legacy `home_win=0`.

Run `PYTHONPATH=src:. python research/post_week4_phase4/reconcile_baselines.py --output /tmp/levline_phase4_baseline_receipt.json` or `pytest -q research/post_week4_phase4/test_reconcile_baselines.py`. The report is descriptive, with zero 2026 outcome use. No automatic refit or model tuning, no production mutations. A full compliant tie-excluded OOS redesign would need a distinct before-result contract, including a new equally retrained comparator; not allowed as a retroactive Phase 3 repair.
