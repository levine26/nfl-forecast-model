# LevLine Props 2.0 — Master Research Charter

Status: **ACTIVE RESEARCH / NOT PRODUCTION AUTHORIZED**  
Frozen V1 benchmark: **51.02% directional accuracy (2,888 / 5,660)**  
Canonical question: **Does LevLine add predictive information after sportsbook information is known?**

## Non-negotiable governance

- Never modify the official LevLine/F-ST winner model from this program.
- Never rewrite frozen V1 historical forecasts.
- Completed 2026 outcomes may grade frozen prospective candidates but may not select features, thresholds, architecture, hyperparameters, sportsbook weights, market horizons, ensemble weights, or prop-family inclusion.
- No supposedly pregame field may be reconstructed from post-kickoff information.
- Research must fail closed when point-in-time provenance is insufficient.
- Negative results remain permanent evidence; no favorable subgroup may rescue a failed preregistered experiment.
- Historical 2023–2025 work is retrospective development evidence, not final promotion evidence.
- Every material challenger receives a contract, exact chronology, immutable inputs, commit SHA, fixed metrics, a fixed decision rule, and a durable result record.

## Dual forecast architecture

### Pure football fair line

Sportsbook player-prop lines and prices are prohibited inputs. Allowed upstream information includes
historical football data, game spread/total, point-in-time availability, role, team/game environment,
matchup state, and source-qualified weather.

Output:
- mean and median;
- fair line;
- full predictive distribution;
- uncertainty / interval coverage.

### Market-anchored probability

Only after the independent football distribution exists:

```
logit(P_final) = logit(P_market) + f(validated incremental LevLine information)
```

The market coefficient remains fixed or strongly anchored near one. The research question is the
incremental residual, not whether LevLine can imitate the market.

## Workstreams

1. **Market microstructure + CLV** — multi-book state, horizons, dispersion, movement, staleness,
   subsequent movement, closing-line comparison.
2. **Game environment** — pace, possessions, situation-adjusted pass/rush state, evolving script,
   red-zone environment.
3. **Dynamic role + availability** — latent opportunity state and OUT/LIMITED/NORMAL/ELEVATED
   workload mixtures.
4. **Routes / target earning** — dropbacks → routes → targets → catches → air yards/YAC.
5. **Contextual efficiency + TD** — mechanism-level expected outcomes plus shrunk player residuals;
   rare-event scoring allocation.
6. **Distribution / simulation** — event-level or mixture distributions with coherent team/player
   accounting and negative-play support.
7. **Evaluation / calibration / ensemble** — rolling-origin evaluation, proper scoring,
   market-residual combination, edge monotonicity, prospective promotion.

## Current evidence boundary

Known development results are recorded in `PROPS_V2_RESULTS_LEDGER.md`.

The strongest current architecture-level evidence is that a low-dimensional market prior improves
substantially over V1, while the LevLine V1 residual itself has not shown stable incremental value
beyond the market. Dynamic role is the strongest football-side direction so far, but its full
multi-season workflow is still completing and remains non-promotional.

## Stop rule

A simpler model that survives chronology, calibration, and prospective evaluation is preferable to a
more sophisticated model with a better retrospective point estimate. Failed experiments are stopped,
recorded, and replaced only by a genuinely new scientific hypothesis.
