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

## Registered identity gate

An already frozen candidate may be rematerialized only if its historical
reconstruction passes the candidate's declared identity policy before any
current-game probability is generated or scored. Candidate ID, canonical
training-data digest, training row count, and season bounds are exact-equality
fields. Floating-point fitted coefficients are reconstruction-parity fields and
must remain inside the candidate's predeclared absolute tolerance.

For `F-ST-01-FROZEN-2026`, the registered artifact constants remain exact and
immutable. Its canonical training digest must equal
`6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0`, and the
three reconstructed coefficients must be within absolute `1e-12` of the
registered constants. This is the same numerical parity bound required by the
production deployment contract; it may not be widened. After the gate passes,
F-ST-01 scoring uses the exact registered constants, never the reconstructed
coefficients.

The identity source must itself be documented. For `F-ST-01-FROZEN-2026`, the
registered values are corroborated by the surviving successful frozen-shadow
artifact from workflow run `34482487521` at head
`5b26693e5d97ec49543b1d778baef63a1d600311`. That artifact is evidence of the
registered frozen identity; it is **not** the missing original pre-fit freeze
provenance.

Every post-freeze rematerialization writes `frozen_identity_check.json` after the
fit and before scoring. A mismatch writes the expected and actual identities,
per-field results, the coefficient absolute deltas, and the active tolerance,
then fails closed. The pre-fit and fit manifests therefore remain uploadable
forensic evidence even when scoring is blocked.

## F-ST-01 recovered numerical runtime and durable evidence

Forensic workflow run `34538432305` (draft PR `#106`) tested a predeclared
OpenBLAS CPU-dispatch matrix using the successful freeze-era package versions and
four threads. Explicit `SKYLAKEX`, and a `NATIVE` runner that auto-selected the
same SkylakeX kernels, reproduced the registered canonical training digest.
Forced non-SkylakeX modes reproduced the previously observed alternate digest
`329c6477f7b80895056b25773bb65da805c12c1a99c68b6c3e04215771c8fa1f`.

The compatible forensic artifact is retained as immutable evidence in
`research/fst/F-ST-01-reconstruction-evidence.json`. It binds the successful
workflow/artifact identity, recovered input hashes, runtime/package fingerprint,
registered frozen identity, reconstructed coefficients, and the original
forensic comparison result. The original forensic script used exact floating
comparison and therefore reported two coefficient mismatches at machine-epsilon
scale; the recorded absolute deltas are approximately `2.22e-16` and `2.50e-16`,
well inside the already-registered `1e-12` reconstruction tolerance. This does
not widen or reinterpret the frozen tolerance.

Routine CI must not force `OPENBLAS_CORETYPE=SKYLAKEX` on arbitrary hosted
hardware: some current runners cannot execute that instruction path and terminate
with `SIGILL`. Instead, the frozen identity gate may be satisfied in either of two
predeclared ways:

1. a fresh reconstruction probe on compatible hardware that reproduces the
   registered training identity within the frozen tolerance; or
2. verification of the immutable compatible-hardware forensic evidence against
   the current frozen specification, including exact evidence/spec hashes,
   candidate identity, rows/seasons, training digest, runtime fingerprint, input
   hashes, and coefficient deltas within `1e-12`.

`scripts/verify_fst_reconstruction_evidence.py` produces the second form of
receipt. The receipt is bound to the current frozen-spec SHA, evidence-file SHA,
and current workflow commit and declares
`receipt_scope=durable_forensic_evidence_verification`. A fresh compatible-hardware
probe declares `receipt_scope=fresh_compatible_runtime_probe`. Unknown scopes,
stale hashes, identity drift, or tolerance widening fail closed.

After either valid receipt is established, current prospective shadow
materialization runs on the runner's native CPU and independently rechecks the
registered training identity. Scoring still uses the exact registered frozen
coefficient literals. The durable evidence path therefore removes a hosted-runner
hardware dependency without changing the model, coefficients, training universe,
probability calculation, or frozen tolerance.

This recovered runtime and evidence are reproducibility constraints for the
already frozen candidate. They are not a hyperparameter search, new model
selection, re-freeze, or use of 2026 outcomes.

## Promotion gate

A candidate may not enter production review unless an independent clean run can
load or reconstruct the admissible historical inputs and reproduce the registered
model identity under the candidate's declared tolerance policy. A mismatch must
fail closed and must not be repaired by replacing the registered digest, widening
parity tolerances, or silently changing historical inputs.

Only artifacts labeled `candidate_freeze` can satisfy the original-freeze
provenance requirement for a candidate created after this contract. A
`prospective_shadow_reconstruction` can diagnose or corroborate behavior, but it
cannot be relabeled as an original capture.

Any architecture, feature, solver, hyperparameter, data-universe, or candidate
identity change requires a new candidate ID. Current-season outcomes may not be
used to select, tune, or rescue a re-freeze whose historical policy prohibits
them.

## F-ST-01

`F-ST-01-FROZEN-2026` predates this persistence contract. Its surviving original
freeze artifacts did not include the complete pre-fit provenance now required for
future candidates. The forensic recovery above identifies a deterministic
compatible runtime that reproduced its registered canonical training identity,
and the immutable evidence plus fresh-probe alternatives provide a fail-closed
way to verify that identity without requiring unsupported CPU instructions on
every current runner. Later reconstruction artifacts must remain labeled
`prospective_shadow_reconstruction`; they do not retroactively become original
freeze captures.
