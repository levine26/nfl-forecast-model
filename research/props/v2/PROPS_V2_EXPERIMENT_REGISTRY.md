# LevLine Props 2.0 — Experiment Registry

Status: **ACTIVE / APPEND-ONLY SCIENTIFIC RECORD**

| ID | Hypothesis | Evidence class | Current state | Frozen decision |
|---|---|---|---|---|
| P2-C1-GLOBAL-MKT | Fixed sportsbook prior + shrunk global V1 residual improves V1 and may improve market | Retrospective 2023–2025 | COMPLETE | Improves V1; does **not** establish incremental market edge |
| P2-C2-ROLE-V01 | Strictly lagged snap-role proxy improves football Fair Lines / direction | Retrospective | COMPLETE | Full mode improves paired MAE; direction not established; route-only rejected; prospective follow-up required |
| P2-NGS-RESIDUAL | Generic NGS residual features add signal beyond market + V1 residual | Retrospective | COMPLETE | REJECT incremental residual |
| P2-FTN-RESIDUAL | Generic FTN matchup residual adds signal beyond market + V1 residual | Retrospective | COMPLETE | REJECT incremental residual |
| P2-MKT-FAMILY | Separate calibration by prop family beats pooled global residual | Retrospective | COMPLETE | REJECT; preregistered gate failed |
| P2-SHADOW-MKT-V1-V01 | Frozen global residual improves market-only probability prospectively | Prospective untouched | PR #379 | Freeze/collect only; no 2026 fitting |
| P2-MICRO-V2 | Player-prop multi-book state / movement adds value vs one OPEN quote | Prospective + historical where licensed | PR #381 — capture layer | Archive exact pregame multi-book states first; no outcome-tuned horizon selection |
| P2-GAME-ENV-V2 | Pregame spread/total context improves top-level opportunity forecasts | Retrospective development | COMPLETE — PR #389 | REJECT V0.1: team-play MAE worsened in all three seasons; pooled clustered CI entirely above zero |
| P2-ROLE-V2 | Latent dynamic role beats static/EWMA proxy | Retrospective | COMPLETE — PR #382 | REJECT V0.2: route-only slightly worsens MAE/CRPS; full materially worsens MAE/CRPS; no subgroup rescue |
| P2-AVAIL-MIX | Q/D workload-state mixtures improve conditional workload vs P(active) × normal role | Historical source audit + prospective follow-up | RETROSPECTIVE BLOCKED — PR #388 | No pre-2025 training examples; stop retrospective test and collect timestamped workload evidence prospectively |
| P2-ROUTE-TARGET | Route → target hierarchy improves receiving process | Source audit | BLOCKED on verified live all-player routes | nflverse participation can support season-lagged pass-play participation, not true all-player routes; see route audit |
| P2-EFF-V2 | Strictly lagged opponent defensive efficiency improves conditional rushing/receiving yardage beyond player baseline | Retrospective component isolation | PR #391 — preregistered component study | Rushing and receiving have separate frozen gates; actual event count conditioning forbids pregame claim |
| P2-DIST-V2 | Signed empirical event-yard distributions improve conditional yardage CRPS vs nonnegative Gamma | Retrospective component isolation | COMPLETE — PR #390 | ADVANCE mechanism only: aggregate CRPS improves; strongest for rushing; actual event count conditioning forbids pregame claim |
| P2-TD-V2 | Overdispersed team offensive TD counts improve rare-event distribution quality vs Poisson at the same mean | Retrospective component isolation | PR #392 — preregistered component study | Gate on CRPS, clustered uncertainty and log loss before any player-TD integration |
| P2-CLV-V1 | LevLine disagreement predicts subsequent market movement | Prospective | DATA CAPTURE STARTED via #381 | Freeze horizon/close selection before grading; no outcome-tuned horizon selection |

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
