# Inner Chronology Freeze

This note is frozen before the canonical ATS-XM target-season execution that uses `chronology_strict_entrypoint.py`.

## Rule

Alpha and beta selection must itself be season-forward. A row from historical validation season `V` is scored only with a KMASS nuisance fit trained on seasons strictly earlier than `V`. The outer target season is never used to choose alpha or beta.

The candidate grids and selection metric remain exactly those in `EXPERIMENT_CONTRACT.md`:

- alpha: `{0, .25, .50, .75, 1.00, 1.25}`;
- beta: `{0, .25, .50, .75, 1.00, 1.25, 1.50}`;
- selection metric: mean multinomial Cover/Push/Loss log loss;
- exact ties prefer the smaller weight.

No result from an earlier non-canonical execution changes those grids or the candidate architecture.

## KMASS nuisance chronology used during inner selection

For validation seasons 2022–2025, reuse the accepted `CONSTANT_SCALE_KEY` nuisance fit for that season from `research/ats-historical-challenger/v2_nuisance_freeze.json`. Those fits are already prior-only relative to their named target season.

The probability archive begins in 2021, while the canonical nuisance freeze begins in 2022. Therefore the 2021 inner-validation rows require one nuisance fit constructed from historical games strictly before 2021. Its structural hyperparameters are not searched here; they are inherited from the accepted constant-scale/key specification:

- Student-t `nu = 30`;
- `lambda_scale = 10`;
- `lambda_key = 1`;
- `conditional = false`;
- `use_key = true`;
- finite key corrections only at `0`, `±3`, and `±7`.

Only the nuisance parameters are fit on the pre-2021 historical rows. The 2021 outcomes never enter that fit.

## F-ST chronology

The F-ST probability for every historical season is reconstructed by fitting the frozen two-input stack on seasons strictly before that season and then scoring the target season. The historical market probability remains the exact archived `market_prob`; no modern moneyline surface is substituted.

## Outer chronology

For outer target season `S` in 2022–2025:

1. every F-ST probability for season `S` is season-forward;
2. alpha/beta selection uses only rows from seasons `< S`;
3. every inner validation row is scored with a nuisance fit trained strictly before its own season;
4. the selected weight is then applied once to the frozen KMASS nuisance fit for outer season `S`;
5. no outcome from season `S` enters nuisance fitting, weight selection, or F-ST fitting.

The canonical execution must preserve an `INNER_CHRONOLOGY_RECEIPT.json` proving the pre-2021 training range and the season-forward selection rule.
