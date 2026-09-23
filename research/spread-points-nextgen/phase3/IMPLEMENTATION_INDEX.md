# Phase 3 Implementation Index

**Program:** LevLine Spread & Points Next-Generation Research Program  
**Phase:** 3 — Controlled Challenger Implementation  
**Production authorization:** none  
**2025 underlying challenger holdout:** unopened  
**Candidate 5:** not trained

## Governance / pre-result freeze

- `PREIMPLEMENTATION_RESEARCH_REVIEW.md` — bounded post-Phase-2 evidence delta and research red team.
- `PRE_RESULT_GATE.json` — machine-readable gate; decision `KEEP_FROZEN_PHASE3_CONTRACT` recorded before development outputs.
- `CANDIDATE_REGISTRY.md` — human-readable frozen A0/B0/C0/D identities.
- `CANDIDATE_REGISTRY.json` — machine-readable candidate registry.
- `FEATURE_PROVENANCE_CONTRACT.md` — frozen data, PIT, state, red-zone, score-tail and market-horizon semantics.

## Shared implementation

- `phase3_scaffold.py`
  - hard 2025 / completed-2026 firewalls;
  - canonical sign/target rules;
  - rolling-origin fold construction;
  - shared metrics and exact-row comparisons;
  - Gaussian/empirical CRPS helpers;
  - season+week block bootstrap;
  - deterministic candidate/provenance receipt assertions.

- `phase3_data.py`
  - loads only 2016–2024 regular-season source data;
  - constructs shifted pregame team state;
  - constructs A0 team rows;
  - reconstructs B0 drives and exact outcome taxonomy;
  - constructs B0 red-zone, turnover, explosive and drive-volume states;
  - constructs the frozen low-frequency rare-score tail.

## Candidate implementations

- `phase3_a0.py` — `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
  - Ridge / Gaussian team-score model;
  - offense and defense team effects;
  - frozen alpha and half-life grids;
  - lexicographic nested tuning;
  - training-only home/away residual covariance;
  - compact OOF strength summaries.

- `phase3_b0.py` — `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
  - independent of A0;
  - L2 Poisson expected-drive model;
  - L2 multinomial TD/FG/EMPTY outcome model;
  - training-only 6/7/8 TD conversion distribution;
  - training-only volume and rare-score variation;
  - deterministic >=10,000-draw final simulation.

- `phase3_c0.py` — `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`
  - consumes only genuine prior-time A0 OOF representations;
  - separate Ridge residual models for margin and total;
  - M0/M1/M2/M3 hierarchy on the same paired rows;
  - market horizon fixed as `historical_closing_late_benchmark_exact_horizon_opaque`.

- `phase3_evaluation.py`
  - score/margin/total/probability/distribution metrics;
  - paired market evaluation and 10,000-draw season+week block bootstrap;
  - frozen diagnostic slices;
  - deliberately small reference baseline set;
  - conditional target-specific D gate with prior-time convex weights only.

## Runner

- `run_phase3.py`
  - one reproducible entry point;
  - hard-capped 2016–2024 source universe;
  - internally generates earlier OOF component rows only where necessary for later prior-time C0/D training;
  - persists Phase 3 headline development evidence only for 2022–2024;
  - never loads or scores 2025;
  - never fits Candidate 5;
  - writes prediction receipts, run manifest, diagnostics and compact future Candidate 5 OOF surfaces.

Canonical command:

```bash
python -m research.spread-points-nextgen.phase3.run_phase3 \
  --output-dir /tmp/levline-phase3 \
  --simulations 10000
```

The CLI rejects a final run with fewer than 10,000 B0 simulations per game.

## Tests / CI

- `tests/test_spread_points_phase3.py`
  - 2025 blocked;
  - completed-2026 selection blocked;
  - exact temporal folds;
  - same-game/future state guards;
  - sign/identity contracts;
  - A0 exact schema;
  - B0 independence/taxonomy/red-zone/simulation reproducibility;
  - C0 A0-only Ridge/null hierarchy/market-label contract;
  - D exact eligibility thresholds;
  - OOF receipt and deterministic bootstrap checks.

- `.github/workflows/research_spread_points_phase3.yml`
  1. compiles Phase 3 implementation;
  2. runs contract/firewall tests;
  3. only after that gate succeeds, regenerates 2022–2024 evidence;
  4. validates output manifest firewalls;
  5. proves the run did not mutate protected production surfaces;
  6. uploads the exact development package.

## Generated evidence location

After the exact regeneration is validated, durable generated artifacts are stored under:

`research/spread-points-nextgen/phase3/generated/`

The expected package is:

- `A0_OOF_2022_2024.csv`
- `B0_OOF_2022_2024.csv`
- `C0_OOF_2022_2024.csv`
- `BASELINES_2022_2024.csv`
- `DIAGNOSTIC_SLICES.csv`
- `FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`
- optional `D_MARGIN_OOF_2022_2024.csv` only if eligible
- optional `D_TOTAL_OOF_2022_2024.csv` only if eligible
- `DEVELOPMENT_SUMMARY.json`
- `CANDIDATE_RUN_RECEIPTS.json`
- `D_ELIGIBILITY_RECEIPT.json`
- `RUN_MANIFEST.json`

No file in the package may contain a 2025 challenger prediction.

## Production firewall

The implementation is research-local. It does not modify or import into:

- frozen F-ST coefficients/artifacts;
- weekly production pipeline;
- Sunday Signal;
- public fair-spread semantics;
- forecast locks or grading;
- official history.

Production remains `F-ST-01-FROZEN-2026`.