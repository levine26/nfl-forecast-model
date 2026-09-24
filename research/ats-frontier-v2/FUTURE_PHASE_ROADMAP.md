# FUTURE PHASE ROADMAP

## Phase 1 — Deep Research & Mechanism Discovery
**Status:** current; research package complete pending closeout.  
**Inputs:** immutable prior LevLine evidence + external literature/code/provider research.  
**Outputs:** failure atlas, source ledger, data matrices, 4-mechanism shortlist.  
**Forbidden:** new Frontier performance.

## Phase 2 — Data Qualification & PIT Reconstruction
**Goal:** determine whether the four mechanism families can be represented with historically reproducible as-of data.  
**Build:** market quote history table; player/lineup state table; chronology/provenance registry; missingness and revision audits; source adapters.  
**Evaluate:** coverage, timestamps, source consistency, joins, as-of reconstruction only.  
**Forbidden:** outcome-based candidate selection or historical Frontier target scores.  
**Exit:** each mechanism `DATA_QUALIFIED` or `DATA_INFEASIBLE`, with immutable data contract.

## Phase 3 — Final Architecture & Preregistration
**Goal:** translate data-qualified mechanisms into exactly specified experiments before target performance.  
**Freeze:** candidate IDs; targets; features; state equations/model family; hyperparameter grids; training windows; outer chronology; market nulls; distribution nulls; proper scores; calibration; uncertainty/bootstrap structure; ATS/selectivity diagnostics; stopping and promotion gates.  
**Forbidden:** target-period result inspection.

## Phase 4 — Historical Development & Ablation
**Goal:** execute the frozen experiments once.  
**Required:** chronology-clean OOF; exact-row market null; proper scores; calibration; distribution diagnostics; candidate-vs-null paired uncertainty; preregistered ablations; season/event robustness; leakage checks; ATS diagnostics.  
**Forbidden:** rescue, new features, hyperparameter expansion after results, outcome-driven threshold tuning.

## Phase 5 — Scientific Synthesis & Survivor Freeze
Classify `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`. Preserve negative results and decision evidence. No fitting/redesign. If zero survivors, stop the program.

## Phase 6 — Prospective Shadow Validation
Only future games after an immutable launch timestamp. Predictions and source snapshots committed before kickoff. Evaluate proper scores, calibration, market-relative performance, ATS, CLV, and actual-price EV where valid prices were captured. No retroactive tuning.

## Phase 7 — Final Synthesis & Human Promotion Gate
Compare prospectively validated candidates with market, F-ST and production. Promotion is never automatic. The user must provide an explicit final green light before any production forecasting behavior changes.

## Anti-redundancy protocol

Every phase must close with: final receipt, exact commit/PR/CI identity, current phase status, next executable action, killed hypotheses and frozen contracts. The next chat reads those artifacts before doing work. This is how the program avoids restarting research or re-running failed ideas.