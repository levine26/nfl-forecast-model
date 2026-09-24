# PHASE 4 INVALID / SUPERSEDED EXECUTIONS

## Run 36023376614 — superseded before evidence acceptance

Status: `INVALID / NOT ACCEPTED`

Workflow: `ATS Frontier V2 Phase 4 frozen evidence`

Execution head: `84546116537ee3550eae91f9e3d5a6a2bc60f7df`

Reason: during the contract-compliance audit, before accepting or interpreting candidate evidence, the implementation was found to encode `STATIC_FOOTBALL_STATE` as an expanding prior-only mean. The frozen M3 preregistration requires the static ablation to use prior-only exponentially pooled/static football summaries. The same audit also identified two evidence-package completeness corrections: M3 state history must be allowed to update from completed prior football games even when a market benchmark row is unavailable, and M4's required ranked-probability/tail diagnostics must be emitted.

Disposition: no metric, OOF prediction, model-selection outcome, or candidate conclusion from this execution is accepted. The run cannot support Phase-4 evidence, candidate disposition, or Phase-5 handoff. If artifacts are preserved by the workflow, they remain superseded evidence only and will be replaced by the accepted exact-head execution package.

Correction classification: `ENGINEERING / CONTRACT-COMPLIANCE`, not scientific rescue. No candidate family, feature channel, latent-state dimension, hyperparameter grid, distribution, key number, market horizon, target, selective subset, or calibration method was added or changed. The static baseline was corrected to the repository-consistent fixed prior-only EWMA half-life of 8 games, with no result-driven tuning, and required diagnostics were completed.

Completed-2026 outcomes used in the correction process: `0`.

Production forecasting changes: `0`.
