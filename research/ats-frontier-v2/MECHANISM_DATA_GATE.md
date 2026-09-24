# MECHANISM DATA GATE

**Evidence cutoff:** 2026-09-23  
**Decision basis:** PIT/data feasibility only; no predictive outcomes used.

| Mechanism | Phase-2 status | Exact reason |
|---|---|---|
| `FRONTIER-M1-DYNAMIC-MARKET-STATE` | `PARTIALLY_QUALIFIED__FREE_FIRST_RECONSTRUCTION_REQUIRED` | Commercial PIT-capable provider semantics are strong, and the free/open-source deep dive found genuine public historical market artifacts across 2020–2025. However, season × game × book × frozen-horizon completeness is not yet empirically established. Public sparse caches/openers/closes may not be relabeled as exact horizons, and rights/provenance must be tracked separately. No purchase is recommended until the free reconstruction is measured and shown inadequate. |
| `FRONTIER-M2-PLAYER-STATE-DELTA` | `PARTIALLY_QUALIFIED` | Lagged ability/replacement quality are feasible; narrow 2025 final-practice T-120 state is previously qualified and 2025+ depth charts are timestamped, but the legacy injury source ends after 2024 and a unified 2022–2025 availability harmonization failed closed. |
| `FRONTIER-M3-HIERARCHICAL-STATE` | `DATA_QUALIFIED` | Core lagged team/QB state can be reconstructed from prior-game nflverse PBP without target-game data. Rich current-week personnel/unit state remains outside this qualification and inherits M2 limits. |
| `FRONTIER-M4-DISCRETE-MARGIN-V2` | `DATA_QUALIFIED` | Historical margin/spread/total fields and a tail-safe integer-bin representation are available. Qualification is numerical/data-only; it establishes no independent alpha and exact PIT market conditioning remains M1-dependent. |

## M1 free-first gate

Before any paid historical-odds acquisition is reconsidered, publish an outcome-blind reconstruction audit that measures, separately by season and frozen horizon:

- exact quote timestamp versus authoritative kickoff;
- active identifiable book count;
- spread line + side-price coverage;
- moneyline coverage;
- total coverage;
- quote age;
- post/equal-kick rejection counts;
- source conflicts;
- temporal class and rights class.

The frozen at-or-before selector remains mandatory. The Phase-3 architecture may narrow M1 to horizons/eras supported by free data only on coverage/provenance grounds fixed before candidate performance is seen.

## Narrowing decisions

- M1 is not killed and is no longer treated as automatically purchase-blocked. Free reconstruction must be exhausted first. The Odds API remains the first commercial fallback only if that audit fails scientifically.
- M2 is narrowed to components/eras with explicit provenance; no unified broad injury-state feature is authorized.
- M3 advances as core dynamic state, not as a backdoor route to unqualified same-week personnel data.
- M4 advances only as a probability-representation experiment.

No purchase, model training, candidate-performance inspection, completed-2026 outcome use, or production change is authorized by this gate.