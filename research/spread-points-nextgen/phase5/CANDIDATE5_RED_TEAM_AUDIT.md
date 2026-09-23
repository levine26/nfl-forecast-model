# Candidate 5 Red-Team Audit

Final audit status: **PASS with scientific disposition `REJECTED`**.

- same-row base-prediction leakage: PASS — A0/B0/C0 OOF assertions and train-through seasons were verified.
- meta-model future leakage: PASS — every fitted target uses only earlier seasons; 2022 is deterministic F-ST fallback.
- outcome-derived feature leakage: PASS — only preregistered pregame component outputs are model inputs.
- post-result feature/component choice: PASS — scientific freeze commit `df14e51d73aad96899d3ba4364cbb76989f0d2bf` predates execution.
- 2025 tuning: PASS — 2025 outcomes never select lambda, features, architecture, or classification.
- completed-2026 contamination: PASS — execution loads historical sources only through 2025; no `outputs/` grading surface is read.
- closing-line-as-T-120 contamination: PASS — C0 is isolated to the diagnostic arm and retains `historical_closing_late_benchmark_exact_horizon_opaque`.
- F-ST surface mismatch: PASS — historical F-ST is reproduced through the accepted chronology-clean annual stack and reproduces 741/1,087.
- game-ID mismatches / duplicate games: PASS — hard one-to-one identity checks.
- scaling leakage: PASS — means/standard deviations are fit on meta-training rows only.
- hyperparameter leakage: PASS — fixed grid and prior-season log-loss tuning only.
- threshold fishing: PASS — winner rule remains strict `P > 0.5`.
- outcome-dependent filtering: PASS — complete-case eligibility is fixed by the feature contract and required finite fields.
- production modifications: PASS — runner writes only Phase 5 research evidence; CI separately diffs protected production surfaces.
- model rescue: PASS — no learner, feature, grid, calibration or threshold changes occurred after results.

The inspection of current 2026 repository state before branching was limited to integration/provenance resolution and did not enter Candidate 5 modeling or grading.
