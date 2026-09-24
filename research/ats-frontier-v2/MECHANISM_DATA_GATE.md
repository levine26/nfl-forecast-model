# MECHANISM DATA GATE

**Evidence cutoff:** 2026-09-23  
**Decision basis:** PIT/data feasibility only; no predictive outcomes used.

| Mechanism | Phase-2 status | Exact reason |
|---|---|---|
| `FRONTIER-M1-DYNAMIC-MARKET-STATE` | `PARTIALLY_QUALIFIED` | Strong PIT-capable provider semantics exist (especially The Odds API; SportsDataIO also viable), but historical real-data access is paid/gated, so book × season × fixed-horizon coverage and missingness are not empirically established. PropLine is prospective-only for this program. |
| `FRONTIER-M2-PLAYER-STATE-DELTA` | `PARTIALLY_QUALIFIED` | Lagged ability/replacement quality are feasible; narrow 2025 final-practice T-120 state is previously qualified and 2025+ depth charts are timestamped, but the legacy injury source ends after 2024 and a unified 2022–2025 availability harmonization failed closed. |
| `FRONTIER-M3-HIERARCHICAL-STATE` | `DATA_QUALIFIED` | Core lagged team/QB state can be reconstructed from prior-game nflverse PBP without target-game data. Rich current-week personnel/unit state remains outside this qualification and inherits M2 limits. |
| `FRONTIER-M4-DISCRETE-MARGIN-V2` | `DATA_QUALIFIED` | Historical margin/spread/total fields and a tail-safe integer-bin representation are available. Qualification is numerical/data-only; it establishes no independent alpha and exact PIT market conditioning remains M1-dependent. |

## Narrowing decisions

- M1 is not killed; it requires authorized historical odds access before Phase 3 can freeze an empirical dynamic-market candidate over the intended era.
- M2 is narrowed to components/eras with explicit provenance; no unified broad injury-state feature is authorized.
- M3 advances as core dynamic state, not as a backdoor route to unqualified same-week personnel data.
- M4 advances only as a probability-representation experiment.