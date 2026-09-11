# LevLine Phase 6 — Zero-Cost Live Data Research

Status: **research planning only**. Nothing in this document authorizes a production source, feature, model, lock change, or use of completed 2026 outcomes for selection.

## Objective

The next model phase should improve the *information set* before it increases model complexity. Historical research has repeatedly shown that generic football-model elaboration does not reliably beat the market. Phase 6 therefore prioritizes genuinely new, orthogonal, point-in-time-safe information while preserving F-ST as the frozen 2026 production probability architecture.

The binding operating constraint is zero recurring paid cost. If a source or capability cannot be sustained at $0, it fails closed rather than becoming a hidden dependency.

## Lane A — Build the LevLine data time machine

The largest long-run research risk is not lack of features; it is inability to prove what was knowable at the decision horizon. We should persist compact snapshots keyed by `retrieved_at_utc`, source-effective timestamp where available, game/player identity, source version/hash, and the target game.

Priority prospective snapshots:

1. **T−120 market state**: named-book de-vigged h2h, spread and total plus robust consensus and source timestamps. Do not store a public raw-odds product.
2. **Depth/roster state**: nflverse 2025+ timestamped depth charts, daily rosters, canonical GSIS identities.
3. **Current player-status state**: Sleeper's documented public `/players/nfl` current fields, captured no more than once daily as the docs request, joined to GSIS through a validated crosswalk. It is a current-state sensor, not a retrospective historical injury feed.
4. **Official injury context**: snapshot the public NFL injury table for audit/explainability when feasible, while preserving the existing rule that rendered pages do not by themselves establish stable historical revision semantics.
5. **Weather**: official NWS hourly/grid forecast at the stadium and decision horizon; retain issuance/retrieval metadata.
6. **Source health**: every capture records success/failure, missingness and freshness so a silent outage cannot become a football signal.

The resulting ledger should live outside normal production outputs and be immutable after the target horizon has passed.

## Lane B — FTN scheme/process ablation

This is the strongest genuinely new historical feature family presently available at zero cost. FTN charting via nflverse covers 2022 onward and includes `date_pulled`, which gives LevLine a direct point-in-time gate.

Pre-register a compact set of team-level prior-state features rather than fishing across every column. Candidate families:

- offensive motion and play-action rates;
- RPO and screen rates;
- shotgun/pistol/under-center mix;
- defensive box count and blitz/pass-rusher distributions;
- QB out-of-pocket rate, QB-fault sack rate and interception-worthy throw rate;
- catchable/contested/drop rates as supporting passing-process state.

For game G, an FTN row is eligible only if its `date_pulled` is earlier than G's modeled decision time and it belongs to a completed prior game. Same-game charting is always prohibited. Evaluation remains chronology-forward through 2025 only.

The primary question is not whether an FTN-enhanced football model beats the old football model. It is whether the new signal adds probability information **conditional on the market** without materially degrading Brier/log loss.

## Lane C — NGS process-state ablation

The repo already loads player-level weekly NGS passing. Extend the research layer—never the frozen production path—to evaluate a small pre-registered QB/process vector where historical coverage is sufficient. Favor variables that describe repeatable process rather than realized box-score output.

Potential categories include time to throw, intended air yards, aggressiveness/completion expectation and rushing/receiving NGS measures where stable. Use prior published state only, carry explicit missingness, and require season-forward validation.

## Lane D — Zero-cost market horizon collector v2

The current near-kickoff collector is h2h-only. A stronger research design is to capture **h2h + spread + total** at a small number of pre-registered kickoff-horizon clusters while staying under the free monthly credit budget with a hard reserve.

The capture scheduler should decide whether a request is due *before* touching the API. Quota headers remain evidence. No paid history and no automatic plan upgrade are permitted.

Derived research features can include:

- per-book vig-free home-win probability;
- robust sportsbook consensus and dispersion;
- spread/total consensus and dispersion;
- source count and freshness;
- movement from T−120 to later pregame horizons;
- cross-market coherence (moneyline probability versus spread/total state).

## Lane E — 2026 outcome-free diagnostics

The 2026 architecture-selection embargo still permits diagnostics that do not use game results. A particularly useful test is whether a T−120 LevLine/market disagreement predicts the **direction of later market movement**. This does not establish game-prediction superiority and cannot authorize promotion, but it can distinguish an early-information signal from arbitrary disagreement.

Other allowed live diagnostics include source coverage/freshness, calibration-input drift without labels, football/market feature drift, book dispersion, and stability of F-ST inputs.

## Lane F — Personnel state without pretending it is injury probability

Timestamped depth-chart movement, roster transactions, current status, prior snap role and replacement quality can improve explainability and may support future research. They are not automatically `P(active)`.

A player-availability probability feature remains blocked until the input can be shown to be free, point-in-time qualified, stably identified and historically evaluable without hindsight. Sleeper prospective snapshots may eventually create such a dataset for future seasons, but they do not retroactively solve 2022–2025 or 2025 injury-history gaps.

## Qualification standard

Every new candidate must be pre-registered before result inspection, use no completed 2026 outcomes for selection, preserve chronology, compare against raw market and frozen/reference LevLine benchmarks, report block-bootstrap uncertainty, and leave `outputs/`/site production semantics untouched. A better accuracy point estimate with worse Brier/log loss is not a win.

## Immediate implementation sequence after the current release closes

1. Add zero-cost prospective snapshot contracts and source-health ledger.
2. Audit exact 2026 schemas for nflverse depth charts/rosters/players, Sleeper current player state, NWS and The Odds API response fields.
3. Pre-register and execute FTN scheme/process ablation through 2025.
4. Pre-register NGS process ablation only if coverage/missingness passes.
5. Redesign the market collector around budgeted h2h/spread/total horizon clusters.
6. Run prospective 2026 market-movement and source-drift diagnostics without outcomes.

No step above changes the production F-ST architecture, T−120 lock, or immutable historical receipts without a separate evidence package and explicit authorization.
