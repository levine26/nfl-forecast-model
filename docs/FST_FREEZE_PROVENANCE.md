# F-ST freeze provenance contract

This contract applies to every future F-ST candidate freeze. It does not change,
repair, or re-freeze `F-ST-01-FROZEN-2026`.

## Required persistence boundary

The exact historical inputs used by an F-ST optimizer must cross a durable
persistence boundary **before** fitting begins. A freeze is not provenance-complete
if it records only coefficients, a model-level digest, a current shadow slate, or
a separately generated OOF artifact.

For every candidate freeze, persist:

1. The exact base out-of-fold matrix used by the nested PURE layer.
2. The exact final F-ST training frame passed to the stack fitter.
3. Stable `game_id` keys for every row.
4. Explicit `row_position` values so the numerical input sequence is recoverable.
5. A raw SHA-256 for the serialized bytes.
6. A canonical game-keyed SHA-256 for semantic row-content identity.
7. A game-ID-sequence SHA-256 for row-order identity.
8. The model's own canonical training-data digest and fitted coefficients after
   the pre-fit artifacts have been persisted.
9. The numerical runtime identity: Python, NumPy, pandas, SciPy, scikit-learn,
   thread-environment variables, and detected BLAS/threadpool backends.
10. An explicit provenance `capture_context` describing whether the files were
    captured during the actual candidate freeze or reconstructed later.

The raw artifact hash and the model training-data digest are different contracts
and must never be substituted for one another.

## Capture-context semantics

Every pre-fit manifest must declare exactly one of these contexts:

- `candidate_freeze`: the input artifacts were persisted during the actual run
  that established a newly versioned candidate's frozen identity, before its
  optimizer executed.
- `prospective_shadow_reconstruction`: the inputs were generated later while
  materializing or evaluating an already frozen candidate. These artifacts may
  be useful forensic evidence, but they are **not** original freeze evidence.

`F-ST-01-FROZEN-2026` predates this contract and may never be labeled
`candidate_freeze` by newly generated provenance tooling. Its current shadow
materialization must use `prospective_shadow_reconstruction`. Any other or
ambiguous context fails closed.

## Serialization

Provenance CSVs use UTF-8, LF line endings, no pandas index, and `%.17g` float
serialization. The raw file preserves execution order. `row_position` makes that
order explicit even after a downstream load or sort.

## Promotion gate

A candidate may not enter production review unless an independent clean run can
load the persisted pre-fit artifacts and reproduce the registered model identity
under the candidate's declared tolerance policy. A mismatch must fail closed and
must not be repaired by replacing the registered digest, relaxing equality
requirements, or silently regenerating historical inputs.

Only artifacts labeled `candidate_freeze` can satisfy the original-freeze
provenance requirement. A `prospective_shadow_reconstruction` can diagnose or
corroborate behavior, but cannot substitute for the missing original capture.

Any architecture, feature, solver, hyperparameter, data-universe, or candidate
identity change requires a new candidate ID. Current-season outcomes may not be
used to select, tune, or rescue a re-freeze whose historical policy prohibits
them.

## F-ST-01

`F-ST-01-FROZEN-2026` predates this persistence contract. Its surviving artifacts
do not include the exact pre-fit historical realization that produced its
registered training identity. This contract is preventive: it must not be used
to relabel a newly reconstructed frame as the original F-ST-01 freeze.
