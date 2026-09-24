# Training Contract

Historical development set: NFL regular-season games 2010–2025 with completed final score and existing repository/nflverse historical `spread_line`. No 2026 row may be loaded. Historical performance is development only.

1. Candidate/null share `nu`. Select `nu` from `{4,6,10,30}` by null-only forward-season validation: for validation seasons 2016–2025, fit the null constant scale on all earlier rows and minimize pooled integer-margin NLL. Ties follow config order.
2. Refit one shared constant scale on all 2010–2025 rows at selected `nu` by null integer-margin MLE, L-BFGS-B, scale bounds `[0.25,80]`, `maxiter=400`, `ftol=1e-11`.
3. Hold `nu` and scale fixed. Fit only `gamma0`, `gamma_abs3`, `gamma_abs7` on all development rows. Objective: mean integer-margin NLL + `10 * ||gamma||² / n`.
4. No prospective refitting during the initial validation window. Missing training score/spread rows are dropped; no imputation.

This procedure is deterministic and frozen before prospective scoring.