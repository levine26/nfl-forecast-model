# LevLine Props 2.0 — Experiment Registry

Status: **ACTIVE / APPEND-ONLY SCIENTIFIC RECORD**

| ID | Hypothesis | Evidence class | Current state | Frozen decision |
|---|---|---|---|---|
| P2-C1-GLOBAL-MKT | Fixed sportsbook prior + shrunk global V1 residual improves V1 and may improve market | Retrospective 2023–2025 | COMPLETE | Improves V1; does **not** establish incremental market edge |
| P2-C2-ROLE-V01 | Strictly lagged snap-role proxy improves football Fair Lines / direction | Retrospective | COMPLETE | Full mode improves paired MAE; direction not established; route-only rejected; prospective follow-up required |
| P2-NGS-RESIDUAL | Generic NGS residual features add signal beyond market + V1 residual | Retrospective | COMPLETE | REJECT incremental residual |
| P2-FTN-RESIDUAL | Generic FTN matchup residual adds signal beyond market + V1 residual | Retrospective | COMPLETE | REJECT incremental residual |
| P2-MKT-FAMILY | Separate calibration by prop family beats pooled global residual | Retrospective | COMPLETE | REJECT; preregistered gate failed |
| P2-SHADOW-MKT-V1-V01 | Frozen global residual improves market-only probability prospectively | Prospective untouched | ACTIVE — #379/#407/#418/#431 merged; 545 legacy receipts preserved; source run 35461495898 persisted first amended batch: 467 provenance-eligible receipts | Frozen coefficients only; failed/missed source runs remain audit-only and are never replayed/backfilled |
| P2-SHADOW-A-DEFENSE | Frozen rushing + receiving opponent-defense residuals improve untouched future pregame distributions vs V1 | Prospective shadow | ACTIVE — #402/#418/#431 merged; 289 legacy receipts preserved; source run 35461495898 persisted first amended batch: 246 provenance-eligible Shadow A receipts across 15 games | Outcomes read 0; started-game skips 0; failed/missed source runs remain audit-only |
| P2-SHADOW-A-GRADER | Grade immutable Shadow A receipts with frozen proper-score and uncertainty policy | Prospective grading | ACTIVE / FROZEN — #406/#418 merged; 246 provenance-eligible Shadow A receipts now persisted; zero eligible outcomes graded so far | Legacy rows are hash/chronology audited then excluded before outcome lookup; 300 decided / 100 games / 8 weeks remain discussion thresholds only |
| P2-SHADOW-B-DEFENSE-ROLE | Shadow A plus Dynamic Role V0.1 full improves untouched future distributions vs V1 | Prospective shadow | ACTIVE — #405/#411/#418/#429/#432 merged; source run 35461495898 persisted first amended batch: 246 provenance-eligible Shadow B receipts across 15 games; baseline V1 reconstruction verified for every game | Dynamic Role V0.1 remains frozen; target outcomes read 0; failed/missed source runs remain audit-only |
| P2-SHADOW-B-GRADER | Score immutable Shadow B receipts primarily vs matched Shadow A and secondarily vs V1 | Prospective grading | ACTIVE / FROZEN — #409/#418 merged before first eligible B receipt/outcome; 246 eligible B receipts now persisted, source-matched to the 246-row A batch; zero eligible outcomes graded so far | Only integrity-matched provenance-eligible A/B receipts enter B-vs-A thresholds; fixed scoring/bootstrap policy; never automatic promotion |
| P2-MICRO-V2 | Player-prop multi-book state / movement adds value vs one OPEN quote | Prospective + historical where licensed | ACTIVE — #381/#413/#418 merged; 4 legacy snapshots / 3,700 rows excluded; provenance-eligible archive now 1,785 rows after 892-row run 35457112800 + 893-row run 35461495898 | Continue untouched timestamped capture; no outcome-tuned horizon selection |
| P2-GAME-ENV-V2 | Pregame spread/total context improves top-level opportunity forecasts | Retrospective development | MERGED TO research/props-v2-challenger — PR #389 | REJECT V0.1: team-play MAE worsened in all three seasons; pooled clustered CI entirely above zero |
| P2-ROLE-V2 | Latent dynamic role beats static/EWMA proxy | Retrospective | COMPLETE — PR #382 | REJECT V0.2: route-only slightly worsens MAE/CRPS; full materially worsens MAE/CRPS; no subgroup rescue |
| P2-AVAIL-MIX | Q/D workload-state mixtures improve conditional workload vs P(active) × normal role | Historical source audit + prospective follow-up | RETROSPECTIVE BLOCKED — PR #388 | No pre-2025 training examples; stop retrospective test and collect timestamped workload evidence prospectively |
| P2-ROUTE-TARGET | Route → target hierarchy improves receiving process | Source audit | BLOCKED on verified live all-player routes | nflverse participation can support season-lagged pass-play participation, not true all-player routes; see route audit |
| P2-EFF-V2 | Strictly lagged opponent defensive efficiency improves conditional rushing/receiving yardage beyond player baseline | Retrospective component isolation | MERGED TO research/props-v2-challenger — PR #391 | ADVANCE both mechanisms: rushing and receiving MAE improve in all three seasons with pooled clustered CIs fully below zero; actual-count conditioning still forbids pregame claim |
| P2-EFF-PREGAME | Opponent defensive efficiency improves full pregame rushing/receiving distributions with V1 opportunities unchanged | Retrospective paired pregame ablation | COMPLETE — PR #394 | PASS rushing and receiving: proper scores + Fair-Line MAE improve; directional accuracy does not improve; prospective shadow eligible only |
| P2-EFF-SHADOW-FREEZE | Freeze final pre-2026 rushing/receiving defensive-efficiency coefficients for prospective shadow | Pre-2026 training freeze | COMPLETE — PR #396 merged into canonical #394 branch; immutable JSON also carried by #402 | Rushing beta 0.10604; receiving beta 0.21008; fit through 2025 football data only; zero 2026 outcomes/props/market results |
| P2-DIST-V2 | Signed empirical event-yard distributions improve conditional yardage CRPS vs nonnegative Gamma | Retrospective component isolation | COMPLETE — PR #390 | ADVANCE mechanism only: aggregate CRPS improves; strongest for rushing; actual event count conditioning forbids pregame claim |
| P2-DIST-RUSH-PREGAME | Signed rushing event support improves full pregame rushing-yard distributions with V1 carry draws unchanged | Retrospective paired pregame ablation | COMPLETE — PR #393 | REJECT: pooled CRPS and MAE worsen; CRPS worsens in 2023/2024; clustered pooled CRPS CI fully above zero |
| P2-TD-V2 | Overdispersed team offensive TD counts improve rare-event distribution quality vs Poisson at the same mean | Retrospective component isolation | MERGED TO research/props-v2-challenger — PR #392 | REJECT: fitted alpha=0 in every season; challenger collapses exactly to Poisson and no score improves |
| P2-CLV-V1 | LevLine disagreement predicts subsequent market movement | Prospective | CAPTURE ACTIVE — 1,785 provenance-eligible archive rows across two valid source snapshots; 3,700 legacy rows excluded; horizon selector reports 894 identities / 1,788 selected horizon rows | Frozen horizon/close policy; repeated timestamp-qualified capture has begun, but do not grade movement/CLV until the preregistered horizon evidence is sufficiently populated |

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

