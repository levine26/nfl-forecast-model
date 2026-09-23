# Candidate 5 Evidence Boundary

## Frozen historical boundary
Phase 4 is complete. A0/B0/C0 2025 component outputs and performance have been observed; 2025 is therefore **OPENED / SPENT** for underlying-model evaluation and is not an untouched Candidate 5 holdout.

Candidate 5 development and selection use only chronology-clean 2022–2024 OOF component predictions, exact-paired with the chronology-clean historical F-ST reproduction. No Candidate-5-specific 2025 metric may be used to choose architecture, features, interactions, preprocessing, lambda grid, threshold, calibration, ablation membership, or classification rule.

## F-ST provenance
Historical F-ST probabilities are reproduced from `challenger_outputs/fst/provenance/training_frame_keyed.csv` by `src/nfl_forecast/challenger_stacking.py::build_chronological_logit_stack`, exactly the provenance route used by the accepted Adaptive Weekly Learning replay. For target season Y, the F-ST stack is fit only on seasons earlier than Y. These are chronology-clean historical reproductions, not original prospective forecast locks.

Production identity remains `F-ST-01-FROZEN-2026`. The final frozen runtime artifact is separately documented in `challenger_outputs/fst/provenance/fit_manifest.json`; it must not be back-applied as an in-sample substitute for historical OOS F-ST probabilities.

## Component provenance
Primary component source: `research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv` (815 rows). Every included A0/B0 row must assert OOF provenance and match the frozen candidate/code/config identities. C0 may be used only in the market diagnostic and must retain `historical_closing_late_benchmark_exact_horizon_opaque`.

## 2025 rule frozen before Candidate-5-specific results
Only after the architecture, feature contract, learner, chronology, tuning procedure, ablations, metrics and classification rules are frozen may the exact frozen model family be run on 2025. If run, the result is labeled `POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`, reported separately, preserved regardless of sign, and may not trigger redesign or rescue.

For that diagnostic, lambda is chosen without 2025 outcomes using only chronology-clean 2023 and 2024 validation predictions from earlier-season meta-training; the selected model is then refit on 2022–2024 and scored once on 2025.

## 2026 firewall
Current repository integration state may be inspected only to preserve unrelated work. Completed 2026 outcomes are not model evidence and must not enter Candidate 5 dataframes, fitting, tuning, grading, feature choice, or interpretation.
