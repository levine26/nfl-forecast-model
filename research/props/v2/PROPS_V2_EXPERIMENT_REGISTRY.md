# LevLine Props 2.0 — Experiment Registry

Status: **ACTIVE / APPEND-ONLY SCIENTIFIC RECORD**

| ID | Hypothesis | Evidence class | Current state | Frozen decision |
|---|---|---|---|---|
| P2-C1-GLOBAL-MKT | Fixed sportsbook prior + shrunk global V1 residual improves V1 and may improve market | Retrospective 2023–2025 | COMPLETE | Improves V1; does **not** establish incremental market edge |
| P2-C2-ROLE-V01 | Strictly lagged snap-role proxy improves football Fair Lines / direction | Retrospective | RUNNING multi-season workflow | No promotion until complete; prospective follow-up required |
| P2-NGS-RESIDUAL | Generic NGS residual features add signal beyond market + V1 residual | Retrospective | COMPLETE | REJECT incremental residual |
| P2-FTN-RESIDUAL | Generic FTN matchup residual adds signal beyond market + V1 residual | Retrospective | COMPLETE | REJECT incremental residual |
| P2-MKT-FAMILY | Separate calibration by prop family beats pooled global residual | Retrospective | COMPLETE | REJECT; preregistered gate failed |
| P2-SHADOW-MKT-V1-V01 | Frozen global residual improves market-only probability prospectively | Prospective untouched | PR #379 | Freeze/collect only; no 2026 fitting |
| P2-MICRO-V2 | Player-prop multi-book state / movement adds value vs one OPEN quote | Prospective + historical where licensed | PLANNED | Contract before data/outcomes |
| P2-GAME-ENV-V2 | Causal game environment improves opportunity forecasts | Retrospective development | PLANNED | V1 vs game-env-only ablation first |
| P2-ROLE-V2 | Latent dynamic role beats static/EWMA proxy | Retrospective + prospective | PLANNED | Estimate state dynamics from role observations, not prop outcomes |
| P2-AVAIL-MIX | Workload mixtures improve distribution quality vs P(active) | Prospective if history inadequate | PLANNED | No fabricated historical limited-state labels |
| P2-ROUTE-TARGET | Route → target hierarchy improves receiving process | Retrospective | PLANNED | Source-quality gate before fit |
| P2-EFF-V2 | Contextual expected outcome + shrunk player residual improves efficiency | Retrospective | PLANNED | Standalone proper-score/Fair-Line test |
| P2-DIST-V2 | Event-level mixtures improve calibration/CRPS/tails | Retrospective | PLANNED | Proper-score improvement required |
| P2-TD-V2 | Hierarchical scoring-opportunity allocation improves TD distributions | Retrospective/prospective | PLANNED | Rare-event distribution metrics required |
| P2-CLV-V1 | LevLine disagreement predicts subsequent market movement | Prospective | BLOCKED on prop market horizons/close | No outcome-tuned horizon selection |

## Experiment discipline

Every new row must specify:
- immutable contract path;
- input provenance and hashes where possible;
- code commit;
- training cutoff;
- forecast horizon;
- evaluation population;
- fixed primary/secondary metrics;
- exact decision rule;
- whether outcomes were previously inspected;
- result artifact and final disposition.

Experiments that fail remain in this table. A new scientific idea receives a new ID rather than
mutating the failed specification.
