# LevLine Props Research Archive — September 2026 Reset

Status: **RETIRED / ARCHIVED FOR CLEAN-SHEET REDESIGN**  
Production status: **DISABLED**  
Archive snapshot branch: `archive/props-pre-revamp-2026-09-21`  
Archive snapshot commit: `f38c1445fcad04e7c8c2ec49b7423f4d232739a8`

This document is the durable written record of the player-prop work completed before the September 2026 repository reset. The full implementation, raw receipts, workflows, tests, UI, contracts, and artifacts that existed at the reset boundary remain recoverable from the archive branch above. They are intentionally removed from the active `main` branch so a future Props system can be designed from a clean foundation.

The archive is evidence and prior work, not an authorization to restore the old system wholesale.

## 1. Why the reset happened

The Props project accumulated too many simultaneously active layers:

- player-state and personnel research;
- opportunity and workload modeling;
- efficiency and touchdown modeling;
- simulation and Fair Line generation;
- multiple market-provider/failover adapters;
- publication and UI layers;
- Props 2.0, 2.1, and 2.2 prospective/research workflows;
- market archives, shadow models, graders, evaluators, and readiness gates;
- many branches and replacement/rebase branches created while the system was evolving rapidly.

The individual governance improvements were useful, but the combined operational surface became disproportionately complex. Props began creating failure modes and maintenance overhead for Sunday Signal itself. The reset therefore separates the stable LevLine/F-ST winner product from player-prop experimentation.

## 2. What was built and learned

### Football-process architecture

The strongest conceptual decision was to model football causally rather than create unrelated black-box Over/Under classifiers.

The working hierarchy was:

```
game environment
→ offensive plays
→ pass/rush allocation
→ dropbacks / attempts / rush opportunities
→ routes / targets / carries
→ receptions
→ efficiency
→ yards
→ red-zone / goal-line opportunities
→ touchdowns
```

That structure should be retained in any redesign. Opportunity and efficiency were separated so a player could change because of workload, role, matchup, efficiency, or availability rather than one opaque projection number.

### Player state, availability, and personnel

Substantial work was completed on:

- point-in-time depth-chart transport;
- player identity normalization;
- role state;
- workload state;
- injury/availability handling;
- participation and snap evidence;
- QB-starter awareness;
- replacement-player context;
- personnel concentration and opportunity reallocation.

A major lesson was that player props cannot be trustworthy if the system merely knows season averages. It needs a point-in-time answer to **who is expected to play, in what role, with what workload, and alongside which teammates**.

The old implementation improved materially here, but current-state personnel data remained one of the hardest operational dependencies.

### Market layer

The project built point-in-time sportsbook handling with:

- sportsbook identity;
- capture timestamps;
- prop type and threshold normalization;
- Over/Under prices;
- implied and no-vig probabilities;
- consensus lines;
- book dispersion;
- market provenance;
- provider failover;
- append-only market evidence;
- later closing-market/CLV matching.

The key scientific lesson is that the sportsbook market must be treated as a **strong benchmark and prior**, not as a weak comparator added at the end.

### Simulation and Fair Lines

The simulation work generated coherent player-stat distributions rather than only binary selections. The system exposed:

- model mean;
- model median;
- Fair Line;
- probability at a sportsbook threshold;
- distributional uncertainty;
- TD-event probability.

That product concept remains valuable. A future system should still answer both:

1. **What should the line be?**
2. **At the sportsbook's actual line and price, what does the model imply?**

### Immutable prospective evidence

One of the most reusable engineering accomplishments was the event-style evidence discipline:

- forecasts were frozen before kickoff;
- forecast receipts were immutable and hash-bound;
- market observations carried timestamps and provenance;
- outcomes were appended later rather than mutating forecasts;
- grading logic was separate from prediction logic;
- chronology failed closed;
- post-kickoff runs could cleanly no-op instead of fabricating pregame evidence;
- completed outcomes were prohibited from silently rewriting the forecast record.

Any future Props implementation should preserve this philosophy, but with far fewer workflows and artifacts.

## 3. Props 2.1 prospective Week 2 evidence

The canonical frozen Props 2.1 cohort was:

- live workflow run: `35477049179`;
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`;
- frozen receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`;
- **3,439 forecasts** across **15 games**.

This cohort is preserved through repository history and the archive branch. It must not be reconstructed or rewritten.

Canonical evaluation produced:

- **1,606 graded forecasts** across **14 finalized games**;
- **359 like-for-like market-matched forecasts**;
- Fair-Line minus original-market MAE difference: approximately **+1.375**;
- game-clustered 95% interval for that MAE difference: approximately **[+0.828, +2.001]**;
- model-minus-market Brier difference: approximately **+0.0243**;
- Brier interval: approximately **[+0.0066, +0.0414]**;
- model-minus-market log-loss difference: approximately **+0.1035**;
- log-loss interval: approximately **[+0.0432, +0.1729]**;
- systematic overconfidence in the preregistered probability bins;
- zero original `MODEL EDGE` observations, so prospective betting ROI was **not measurable**.

Positive differences above mean the frozen Props 2.1 model was worse than the matched point-in-time market on those loss/error metrics.

The scientifically correct conclusion from that cohort was: **Props 2.1 did not demonstrate incremental predictive accuracy beyond the contemporaneous market.** It was useful diagnostic evidence, not evidence of a market-beating system.

## 4. Props 2.2 work and its correct interpretation

Props 2.2 was designed as a future-holdout market-residual experiment after the 2.1 result.

The frozen candidate family included:

- the Props 2.1 control;
- line residual blends;
- probability residual blends;
- probability shrinkage diagnostics;
- combined market/model residual challengers.

Only two combined challengers were designated promotion eligible. The design required future untouched evidence, clean chronology, game-clustered uncertainty, minimum sample thresholds, and multiplicity control.

Important: **Props 2.2 never produced a legitimate future prospective ledger before this reset.** It therefore has no valid outcome-based performance claim and no selected winner. Its code and preregistration are archived as methodology work only.

## 5. Distribution and uncertainty research

The project explicitly moved away from treating a projection mean as sufficient evidence. Research work considered preservation/evaluation of:

- prediction distributions;
- interval coverage;
- calibration;
- dispersion;
- tail behavior;
- proper probability scores;
- market-relative residual information.

This is worth retaining. A clean redesign should evaluate the **distribution**, not merely whether a point estimate beat a line.

## 6. What worked well

The following ideas should be candidates for reuse:

1. **Football decomposition** — opportunity before efficiency, role before result.
2. **Point-in-time player state** — depth chart, injury, availability, QB starter, workload.
3. **Market as a first-class benchmark** — same player, same market, same threshold, valid timestamp.
4. **Distributional forecasting** — mean/median/Fair Line/probability/intervals.
5. **Immutable pregame receipts** — never rewrite what the model actually knew.
6. **Separate grading** — append outcomes after games instead of contaminating forecast artifacts.
7. **Chronology gates** — data horizon <= forecast time < kickoff.
8. **Fail-closed publication** — unavailable or stale evidence should not silently become a confident forecast.
9. **Clean post-kickoff no-op semantics** — no fake pregame capture after the game starts.
10. **Prospective evaluation against the market** — proper scoring rules and paired error, not only hit rate.
11. **Personnel/opportunity awareness** — injury/news context must affect the football inputs before projection, not only appear in prose.

## 7. What did not work well

### The model did not establish market superiority

The only substantial frozen prospective cohort available at reset showed the market outperforming Props 2.1 on matched Fair-Line error, Brier score, and log loss. This must remain part of the project history.

### Overconfidence

Probability outputs were too confident relative to realized outcomes. Any redesign needs calibration as a primary objective, not an afterthought.

### Operational coupling

Props became entangled with:

- the Sunday Signal dashboard deploy;
- GitHub Pages publication;
- live media-trigger chains;
- multiple scheduled collectors;
- multiple shadow/evaluation workflows.

A research failure or lifecycle edge case could therefore create noise around the stable winner product. Future Props research should remain isolated until it earns integration.

### Too many branches and workflows

Rapid experimentation produced a large branch/workflow surface with duplicate rebases, superseded implementations, legacy listeners, and handoff branches. Even correct individual changes became difficult to reason about globally.

### Artifact growth

Immutable evidence is necessary, but storing large recurring JSONL ledgers directly on `main` is not a sustainable transport strategy. At reset, stress testing showed that an eight-challenger Props 2.2 ledger for a Week-2-sized source cohort could plausibly exceed GitHub's 100 MiB single-file limit.

Future large raw evidence should live off the production branch in bounded shards or a dedicated data/evidence store.

### UI arrived too early

The product surface was repeatedly redesigned while model validity was still unsettled. A future rebuild should defer a polished public Props UI until the scientific pipeline has a credible prospective record.

## 8. Cleanup decision

As of this reset:

- Props is removed from the Sunday Signal production UI.
- Props live/scheduled workflows are removed from `main`.
- Props model, market, simulation, publication, research, and test code is removed from `main`.
- Raw Props artifacts and challenger ledgers are removed from the active branch.
- Sunday Signal remains the LevLine/F-ST winner product.
- The complete pre-reset state remains recoverable on `archive/props-pre-revamp-2026-09-21`.

This is intentional retirement, not accidental deletion.

## 9. Clean-sheet rules for the next Props generation

A future Props 3.0 / successor should start with these constraints:

1. **One canonical research branch.** No parallel forest of overlapping implementation branches.
2. **One minimal prospective pipeline.** Capture → freeze → grade → evaluate.
3. **No public UI at first.** Produce machine-readable research evidence before product polish.
4. **No dependency on Sunday Signal publication.** Research failures must not affect the winner site.
5. **Market benchmark from day one.** Every supported market should have a same-threshold point-in-time comparator where available.
6. **Player-state gate before simulation.** Starter, availability, role, and workload must be resolved or uncertainty explicitly modeled.
7. **Full distributions, calibrated probabilities.**
8. **Immutable receipts and strict chronology.**
9. **Large evidence stays off `main`.** Keep `main` small.
10. **Prospective validation before any claim of edge.**
11. **No tuning on the evaluation cohort.**
12. **No production promotion unless the model demonstrates incremental information beyond the market with sufficient untouched evidence.**

The next design may reuse archived concepts, but it should not mechanically resurrect the old architecture.

## 10. Where the old material lives

Full snapshot:

`archive/props-pre-revamp-2026-09-21` at `f38c1445fcad04e7c8c2ec49b7423f4d232739a8`

Use that branch for historical inspection of:

- `research/props/**`;
- `src/nfl_forecast/props_*.py`;
- Props 2.1 and 2.2 contracts/evaluators;
- market/shadow workflows;
- simulation/opportunity/efficiency code;
- UI components;
- raw output and challenger receipts;
- tests and live orchestration.

Do not merge the archive branch back into `main`. Extract individual ideas deliberately into a new design.
