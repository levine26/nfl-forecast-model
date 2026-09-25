# M1 Prospective Phase 2 Operator Checklist

Use this checklist only for `FV2-PROS-M1-MARKETSTATE-01` while Phase 2 is active.

- [ ] Confirm scheduled run uses current `main`.
- [ ] Confirm outcome-blind horizon qualification runs before any provider request.
- [ ] Confirm provider request is made only when the frozen due gate is open, except explicit manual workflow dispatch.
- [ ] Confirm predictor horizons remain `T-2160m`, `T-720m`, `T-360m`, `T-120m`.
- [ ] Confirm `T-60m`, `T-30m`, and `LATEST_PREKICK` remain diagnostic-only.
- [ ] Confirm no fixed-horizon observation is accepted after its target timestamp.
- [ ] Confirm at least two complete books are required for a qualifying consensus capture.
- [ ] Confirm collector skip/failure reason is durably persisted.
- [ ] Confirm qualification ledger is refreshed after each successful capture and on no-due scheduled runs.
- [ ] Confirm all evidence persists only to `research-data/m1-market-state-v1`.
- [ ] Confirm completed-2026 outcomes used = `0`.
- [ ] Confirm no model fitting, CPL scoring, ATS accuracy, calibration, ROI, or production deployment occurs in Phase 2.

Phase 2 may advance only through a separately documented, outcome-blind closeout based on real prospective evidence.
