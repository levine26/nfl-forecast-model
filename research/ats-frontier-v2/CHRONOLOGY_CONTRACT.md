# CHRONOLOGY CONTRACT

## Global rule

No random K-fold. No target-game future information. Every transformation, scaler, state, distribution parameter and hyperparameter must be learned from information available strictly before the row's prediction time.

## Historical development population

Primary evaluation population: NFL regular-season games in 2022, 2023, 2024 and 2025 with the exact fields required by the candidate/null pair.

These seasons are development/non-pristine. No statement may call them an untouched holdout.

Historical training/state history begins in 2010. Games before 2022 are used only to train/warm state and tune in chronology-clean fashion. Completed 2026 outcomes are sealed.

## Outer walk-forward

For each target season `Y ∈ {2022, 2023, 2024, 2025}`:

1. hyperparameters are selected only from games preceding season `Y`;
2. target-season Week 1 is predicted using data through the end of the prior season;
3. for target-season Week `w > 1`, models/states may update using completed games from weeks `< w` only;
4. target week games are scored only after all predictions for that week are frozen.

No later week may influence an earlier week.

## Inner tuning

For each outer season, select hyperparameters using expanding chronological validation over the **three most recent completed seasons** available before that outer season. When a candidate requires longer state warm-up, earlier data may initialize the state but may not enter the validation score for hyperparameter selection.

Example: outer 2022 tuning scores 2019–2021; outer 2023 scores 2020–2022, where 2022 predictions used their own prior-only chronology.

Primary inner selection uses the candidate's preregistered proper score, never ATS hit rate or ROI.

Tie rule: if two configurations differ by less than `1e-4` mean primary score, choose the simpler configuration in this order:

1. larger regularization;
2. lower state/process dimensionality (when applicable);
3. larger Student-t `nu` / less tail flexibility for M4.

This deterministic tie rule replaces post-result discretion.

## Preprocessing

- Standardization moments: prior-only training rows.
- Missing-value policy: explicit preregistered missing indicators or fail closed; no target-era global imputation.
- Team aliases: static canonical mapping.
- Publication/stat-correction lag: a target row may use only completed prior-game data already represented in the qualified source; target-game PBP is forbidden.
- Same-game snaps, final inactive lists, final starters, gamebooks and realized weather are forbidden as pregame features unless separately timestamp-qualified before the horizon.

## Candidate/null pairing

Every candidate-v-null metric uses the intersection of rows where both produced valid frozen predictions. A candidate may not gain apparent performance by silently dropping hard games. Coverage differences are reported separately.

## Postseason

Postseason games may update future latent states after completion, but are excluded from the primary 2022–2025 regular-season score. Any postseason diagnostic is secondary and cannot affect selection.

## 2026 firewall

No completed-2026 game outcome may be used for fitting, tuning, calibration, architecture selection, feature selection, threshold selection, or Phase-4 historical evidence.