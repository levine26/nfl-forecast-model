# Candidate C Prospective Shadow — Implementation and Preflight

**Status until artifact freeze:** `NOT_FROZEN`. After successful tested freeze: `INFRASTRUCTURE_READY / AWAITING_ELIGIBLE_LOCKS`, not predictive validation. **No 2026 outcome included in training.**

Authoritative preregistration: [C_PROSPECTIVE_PREREG_2026_10_07.md](C_PROSPECTIVE_PREREG_2026_10_07.md), committed in PR #629 *before* this implementation. Fixed historical model: `EARLY-STATE-SHRINKAGE-V1-SHADOW-2026-10-07`, locked F-ST incumbent `F-ST-01-FROZEN-2026`. No production changes.

## Tested components

1. `freeze_c_model.py`: exactly once, use checked 2012–2025 historical NFL PBP/schedules and the recovered hash-verified 2020–2025 1,615-game F-ST OOF; reconstruct *same C state* using earlier completed games, fit fixed-offset logistic L2=0.02, persist all model coefficients/standardizers/training/source hashes/freeze time in `artifacts/C_SHADOW_FROZEN_2026.json` on this research branch. No 2026 training inputs or new feature search. The original frozen historical training labels include ties coded as away wins; this known limitation is not retrospectively repaired.
2. `c_shadow.py`: pure, side-effect-free inference from a **strict PIT snapshot**; recomputes C offense/defense state and prior-game uncertainty from captured past-game evidence; rejects future/late source timestamp, staleness, duplicate/mismatched team games, unknown locked F-ST identity, unqualified upstream completeness audit, or invalid probability. Does not retrieve the current outcome or change F-ST. `run_c_shadow.py` is a **manual offline** scoring adapter and writes a prediction once using exclusive creation; it cannot overwrite an earlier capture.
3. `c_shadow_eval.py`: later, read existing frozen prediction records and independently verified official postgame scores. Require result observed >=3h after kickoff, matching game/week, and verified result-source hash. Grade only non-ties; report ties separately. Until >=200 *new* eligible non-ties across >=14 distinct weeks, no formal gate. At the formal gate compute paired accuracy (priority), switches, proper scores and 2,000 week-block bootstrap. Always `promotion_authorized=false`. This is NOT a backtest and NEVER uses 2026 outcomes for fitting.
4. `test_c_shadow.py`: synthetic positive and negative fixtures cover chronology, source identity, duplicates, late scores, ties, model immutability and predictions that cannot be overwritten. Synthetic probabilities **are not accuracy evidence**.

## Explicit operational limitation

**No automatically scheduled collector or already-qualified prospective game has been demonstrated.** A snapshot must be captured **before** the *actual official F-ST lock* with compatible source timestamps. Merely generating C on a later date using past games or today's NFL injury report is not point-in-time evidence. The `upstream_completion_audit_passed` and source hashes are *mandatory attestation fields*, not independent proof that a provider supplied a genuinely complete data archive. Before treating a game as formally eligible, an independent upstream source/fixture audit must substantiate the event list, source clocks, source/license permissions and contemporaneous official lock receipt. If those checks are unavailable, do not score or claim a valid prospective comparison.

Daily/weekly scheduling is **not** activated here: connecting to official lock ingestion or otherwise automating capture changes the timing and operational contract and requires verified upstream access. There is no 2026 candidate result in this package. The snapshot scorer itself is ready for a qualified, separately approved source adapter; historical fitting and scoring are decoupled so future accumulation never triggers automatic model training or model selection.

## How to run a *verified* input, not historic backfill

```bash
PYTHONPATH=src:. python research/post_week4_phase4/run_c_shadow.py \
  --frozen-model research/post_week4_phase4/artifacts/C_SHADOW_FROZEN_2026.json \
  --pregame-snapshot /path/to/immutable_pre_lock_snapshot.json \
  --output /path/to/append_only_research_capture/2026_XX_AWAY_HOME.json
```

Do not commit the raw snapshot to public `main` or show licensed payloads. No automatic promotion; F-ST remains authoritative. Repository test workflow `.github/workflows/research_post_week4_phase4_c.yml` verifies the one-time artifact independently from legacy production.

## Remaining scientific gates

- Exact C model coefficients frozen and hash-verified on 2012–2025 prior-game history.
- Independent production-lock source adapter + source/capture timestamp proof (not yet available).
- Prospective non-tie population reaches at least 200 games and 14 weeks.
- Positive season/week-robust paired winner edge, nonpathological proper scores, no PIT provenance defects.
- Explicit user promotion approval, then separate reversible production PR. **Not authorized now.**

## Preflight receipt — 2026-10-07

The one-time research freeze passed GitHub Actions [run #37697761899](https://github.com/levine26/nfl-forecast-model/actions/runs/37697761899). Frozen artifact: `artifacts/C_SHADOW_FROZEN_2026.json`, saved at `2026-10-07T22:47:31+00:00`. It records **1,615** historical (2020–2025) fitting rows, `outcomes_2026_used=0`, L2 penalty 0.02, the same three C features, and immutable historical feature-builder/source digests. The model's saved parameters and proper source provenance have been checked. The frozen artifact **must not be refit** during later shadow captures. Synthetic unit tests pass; no real pre-lock 2026 Candidate C capture has been qualified, and no statistical superiority is claimed.
