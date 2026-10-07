# Phase 4 B/C — Two-stage Candidate C capture gateway and synthetic QA

**Status:** ENGINEERING_GATEWAY_IMPLEMENTED / LIVE_VERIFIERS_MISSING / NO_QUALIFIED_PREDICTIONS.
**Model:** frozen artifact \`artifacts/C_SHADOW_FROZEN_2026.json\` — no coefficient, feature, threshold, fit or pre-2026 training changes.
**Only research paths.** The gateway is *not deployed* to the weekly, pregame or Sunday Signal workflow. Do not ingest the example synthetic tests as prospective results.

## Two-stage contract

1. \`capture_raw(raw, restricted_store, source_verifier=..., clock=...)\`: stage football-only, complete earlier team-game evidence before the F-ST lock. Clock is measured **when the function actually runs**; the caller cannot supply a historical \`snapshot_captured_utc\`. Captures include raw-input hash, source clocks and expected completed-game audit. A callback must independently attest PIT coverage, source rights and storage permissions; without it the stage remains provisional and cannot be sealed. The stored JSON may contain provider data: **keep it in a private permitted filesystem**, not GitHub.
2. \`seal_against_lock(store, game_id, original_lock_row, frozen_model, lock_verifier=..., clock=...)\`: after the original locked F-ST row first appears, require a separate externally implemented verifier to attest its *first* GitHub/API publication timestamp, commit identity and exact row digest. Match official game/week/teams/kickoff, F-ST strategy/artifact, probability, original market state, lock and forecast clocks. Require real scoring clock before kickoff. The pre-lock stage cannot be revised.
3. Deterministic game-relative paths + OS exclusive-create protect against accidental duplicate overwrite. Existing sealed records can only be replayed when the digests agree. All unqualified attempts create distinct JSON receipts under \`failures/\` without raw data. Failures remain ineligible. The model itself delegates exclusively to frozen \`c_shadow.score_snapshot\` (no fit, no outcome read).
4. Predictions are output only by an independently provided verifier. The test suite uses *deliberately synthetic mock verifiers* and does not establish GitHub server timing or data rights.

## Trust boundary and blockers

The current implementation has **NO LIVE SOURCE VERIFIER AND NO LIVE LOCK-PUBLICATION VERIFIER**. Running a Python process with a fake clock or fake callback is not proof of a prospective observation. The UTC host clock and local file \`O_EXCL\` writes by themselves are not a trusted time authority or a tamper-proof WORM store. A prospective operator needs independently verified source-age/completeness evidence, an acceptable monotonic/externally audited UTC clock, write-once audit-storage durability, reproducible provider per-game data, and a GitHub first-appearance/received-before-kickoff proof. The actual \`prediction_history.csv\` is mutable and may be published asynchronously after its \`lock_timestamp_utc\`. No supplied callback guarantees have been met in the live repository.

Until those conditions are met, **NO live job** should import, invoke, or run this gateway and **NO result is a qualifying prospective Candidate C prediction**. The separate outcome-only evaluator is an offline statistical function, not a validator of independent provenance; an upstream qualification audit must gate its production inputs. This protects against falsely counting historical or synthetic records.

## QA scope

\`test_two_stage_gateway.py\` uses deterministic synthetic fixtures to test: valid pre-lock raw capture → first-publication F-ST proof → frozen scorer → sealed output → pending result/tie exclusion; idempotent retry; conflicting capture refusal; missing/late source; missing coverage; future observed stats; label leakage; wrong team/week/kickoff; missed/recovered lock; wrong model; stale/missing market; late official generation; unverifiable or after-kickoff publication; after-kickoff scoring; missing artifact; and durable failure ledger.

No public forecast, production results, model coefficients, training/evaluation contract, or official ATS path is edited.

## Next objective

Implement and independently validate a **genuine read-only source adapter** and **official first-publication lock verifier** before allowing any actual live qualification. Only schedule collection after source terms and timestamp validity are proven. Continue collecting until at least 200 eligible new non-tie games across 14 weeks before formal evaluation.
