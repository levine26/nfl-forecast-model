# Phase 3 Adversarial Red-Team Audit

The purpose of this audit is to try to invalidate the Phase 3 development evidence, not to improve its headline results.

## Data / chronology

- **2025 access:** PASS. The loader requests only 2016-2024; manifest records 2025 loaded=false and scored=false.
- **Completed-2026 contamination:** PASS. Guard rejects 2026+ target seasons; manifest records completed-2026 outcomes used=false.
- **Same-game PBP leakage:** PASS. Pregame process states are shifted by one completed team game; regression tests verify the current game cannot alter its own state.
- **Future opponent-state leakage:** PASS. Opponent state is joined only after shifted team state construction for the same pregame row.
- **Target-season preprocessing leakage:** PASS. sklearn pipelines are instantiated unfitted and trained inside prior-only folds/outer training.
- **Inner/outer chronology:** PASS. Exact inner seasons are shared from the scaffold; prior-only assertions reject train max >= validation min.
- **A0 covariance leakage:** PASS. Home/away residual covariance is estimated on the outer training set only.
- **B0 current-game drive leakage:** PASS. Target-game drive outcomes are never used as pregame states; drive EWMAs/cumulative red-zone states are shifted/prior-only.

## Identity / source semantics

- **Game/team identity:** PASS. Shared schedule scaffold and identity tests are active.
- **Schedule/PBP schema drift:** FIXED AND RETESTED. Initial full regeneration failed because overlapping PBP schedule identity columns were suffixed on merge. The defect was repaired by canonicalizing schedule-owned columns before the join and a regression test was added. No candidate specification changed.
- **Market sign/orientation:** PASS. Positive spread line is consistently interpreted as market-implied home margin; reconstruction tests cover total/margin -> team points.
- **Market alignment:** PASS. C0 and market comparisons use game-id paired rows; 815 common 2022-2024 rows are preserved.
- **Market horizon honesty:** PASS. Historical rows remain labeled `historical_closing_late_benchmark_exact_horizon_opaque`; no T-120 claim is made.

## Candidate-contract checks

- **A0 exact schema/grid:** PASS. Frozen feature schema and alpha/half-life grids are test-pinned.
- **B0 independence from A0:** PASS. B0 feature lists contain no A0 output/state.
- **B0 taxonomy/red-zone/tail:** PASS. TD/FG/EMPTY taxonomy and red-zone prior constant are test-pinned; simulation is deterministic by game/candidate seed.
- **C0 uses A0, not retrospective winner:** PASS. Frozen C0 feature hierarchy references A0 and contains no B0 input.
- **C0 estimator:** PASS. Ridge-only frozen grid.
- **M0/M1/M2/M3 identical target rows:** PASS. All arms are generated from the same paired C0 target frame.
- **D stacking leakage:** PASS. Blend weights are fit only on prior seasons for each target season; receipts preserve training seasons and weights.
- **D threshold drift:** PASS. Frozen eligibility thresholds are test-pinned and both targets remain ineligible.
- **Post-result model rescue:** PASS. No expanded grid, alternate count family, nonlinear C0, A1, or forced ensemble was introduced after development evidence.

## OOF / reproducibility

- **OOF receipt integrity:** PASS. Every A0/B0/C0 development row has train-through season < target season.
- **Future Candidate 5 surface:** PASS. 815 rows; all A0/B0/C0 train-through fields are prior to target season and `oof_provenance_assertion` is true.
- **Candidate identity drift:** PASS. deterministic candidate IDs are test-pinned.
- **Simulation stability:** PASS for reproducibility; B0 uses deterministic 10,000-draw seeds. Its wide intervals and total bias are retained as evidence, not tuned away.
- **Exact evidence reproducibility:** hardened Phase 3 CI regenerates the package and byte-compares the frozen CSV/JSON evidence on the final head (except the run manifest's Git-head field).

## Production firewall

- **Production code/model changes:** PASS. Dedicated CI diffs protected production surfaces and the Phase 3 implementation lives under research/test/workflow paths.
- **Production model:** remains `F-ST-01-FROZEN-2026`.
- **Sunday Signal behavior:** unchanged.

## Research-gate red team

The preimplementation review explicitly discounted random train/test splits, opaque performance records, closing-line/early-horizon conflation, hindsight starter/injury information, repeated model/feature selection and threshold-selected sportsbook-beating claims. Negative evidence favoring shrinkage/simple models was retained. The decision remained `KEEP_FROZEN_PHASE3_CONTRACT`.

## Final red-team disposition

No methodological defect was found that invalidates A0, B0 or C0 as Phase 4 references after the schedule/PBP merge defect was fixed and regenerated. The weak/negative development performance is therefore preserved as a scientific result rather than treated as invalidity.
