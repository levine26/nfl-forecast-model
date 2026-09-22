# Active LevLine / Sunday Signal Workstream Handoff

**Point-in-time:** 2026-09-21 ~18:36 America/Los_Angeles  
**Repository:** `levine26/nfl-forecast-model`

This file is a continuity aid, not a substitute for checking current GitHub state. Before acting, re-read current `main`, open PRs, and relevant workflow runs. Do not restart completed work.

## Non-negotiable governance

- Do not modify the official LevLine/F-ST winner model while working these lanes.
- Do not weaken research firewalls, chronology, locking, or publication gates to make CI pass.
- Week 2 Props outcomes are **evaluation/diagnostic evidence only**. They may motivate future hypotheses but may not be used to fit coefficients, choose among challenger weights retrospectively, tune thresholds, recalibrate probabilities, or construct retrospective betting signals.
- Props 2.2 promotion is future-holdout only.

## Sunday Signal checker / editorial recovery

### What is already fixed

- Post-kickoff slate contraction was identified as the main editorial failure mode.
- PR #455 added a persisted weekend editorial-roster concept.
- PR #456 hardened Groq publication against isolated challenger-output races.
- PR #465 added recovery from the newest **launch-grade historical full-slate editorial snapshot**. The recovery restores only editorial artifacts, trims them to the authorized 15-game Week 2 weekend roster, preserves current Groq failure targets, and never changes LevLine/F-ST forecasts.
- The fallback manifest was retriggered on current main for the exact unresolved set.

### Current recovery run at this handoff

- Fallback workflow: **Sunday Signal ChatGPT failed-game fallback**
- Run: **35675981382**
- Trigger commit: `cf2c8cbe11b2492188ce1674a04c4c981ef0d2be`
- Target: six unresolved games.
- At handoff the run was queued because GitHub Actions was saturated by parallel research CI.

### Do not call Sunday Signal fixed until all of these are verified on committed main

1. `inputs/sunday_signal/editorial_slate_roster.json` exists and represents the frozen 15-game weekend roster.
2. `outputs/copilot_media_reads.json` contains exactly those 15 games.
3. `outputs/game_previews.json` contains exactly those 15 games.
4. `outputs/contextual_evidence.json` contains exactly those 15 games.
5. `outputs/context_source_status.json` reports healthy full-slate editorial/media counts (15), with no stale partial-slate health claim.
6. Current failed-game targets are either resolved by validated ChatGPT payloads or remain explicitly degraded; never hide unresolved games.
7. The dashboard deployment consuming the repaired artifacts succeeds.
8. No winner probabilities, F-ST calculations, locks, grading, or betting-model outputs changed as part of editorial recovery.

If the fallback run is cancelled by unrelated main churn, re-check the current unresolved game IDs before retriggering. Do not blindly reuse a stale manifest.

## Props 2.1 — current scientific state

### Engineering fixes already merged

- **PR #446** — point-in-time depth-chart transport into live Props 2.1. Depth-chart evidence is categorical role context only; it does not create workload certainty or betting eligibility.
- **PR #459** — fully started target week becomes a clean live no-op instead of a false production failure.
  - Verified production run: **35675291033**
  - It detected all 16 Week 2 games as started, wrote `levline-props-postkickoff-noop-v0.1`, preserved the last valid Props publication, and exited successfully.
- **PR #466** — canonical current-main prospective evaluation surface for the frozen Week 2 cohort.

### Frozen Week 2 evidence

Frozen cohort:
- source live run: `35477049179`
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- 3,439 frozen Props 2.1 receipts / 15 games.

Successful prospective evaluation found:
- 1,606 forecasts graded across 14 finalized games at the evaluation point.
- 359 like-for-like market-matched forecasts.
- On that matched one-week cohort, Props 2.1 was worse than the contemporaneous sportsbook market:
  - model/fair-line projection MAE delta vs market: about **+1.375** units, game-clustered 95% CI roughly **[+0.828, +2.001]**;
  - Brier delta vs market: about **+0.0243**, CI roughly **[+0.0066, +0.0414]**;
  - log-loss delta vs market: about **+0.1035**, CI roughly **[+0.0432, +0.1729]**.
- Preregistered probability bins showed systematic overconfidence.
- There were zero original `MODEL EDGE` observations, so betting ROI is not measurable.
- This is **not** enough evidence to declare permanent model failure or market superiority across future weeks, but it is enough to reject any claim that Week 2 demonstrated market-beating Props accuracy.

Do not tune against these results.

## Active Props PRs and intended order

### #468 — Preregister Props 2.2 market-residual future-holdout challengers

Purpose: freeze a small outcome-free grid before future-holdout capture.

Frozen candidates:
- unchanged Props 2.1 control;
- market-residual line blend with 25% model residual;
- market-residual line blend with 50% model residual;
- 50% shrinkage of model probability toward 0.5;
- combined 50% residual blend + 50% probability shrinkage.

These weights are simple prespecified fractions and are **not fitted to Week 2**.

Promotion threshold is at least:
- 3 future weeks,
- 30 finalized games,
- 1,000 market-matched observations,
- 250 observations for a prop-family superiority claim,
- clean chronology/receipt integrity,
- game-clustered uncertainty.

**Merge #468 first after its preregistration/firewall checks pass.**

### #471 — Implement preregistered Props 2.2 transformations

Stacked on #468. It implements only the frozen deterministic transformations and explicitly rejects outcome-contaminated inputs.

At this handoff it is based on an older prereg branch/main state and is not mergeable. **Do not merge the stale branch.** After #468 lands, rebuild/rebase #471 on current main while preserving only the preregistered transformation code/tests.

### #474 — Preserve source distribution evidence in future Props 2.1 receipts

Current-main replacement for stale #469.

Forward-only evidence preservation:
- SD,
- prediction interval and coverage,
- simulation count,
- TD count distribution,
- expected TDs,
- pure simulation seed,
- source-model hash.

This is stored only in future immutable research receipts. Public challenger output stays unchanged. Frozen Week 2 receipts are not rewritten. The receipt explicitly says a lossless continuous distribution is not preserved, so CRPS/PIT remain unavailable unless a separate prospective archive contract is added.

This lane is independent of Props 2.2 and may merge after its checks pass.

### #473 — Diagnose frozen Props 2.1 Week 2 miss without tuning

Descriptive-only error decomposition by preregistered subgroup:
- prop type,
- position,
- role state,
- availability,
- workload,
- market liquidity,
- forecast horizon.

It may report MAE/Brier/log-loss gaps and confidence gaps. It may **not** fit calibration, search thresholds, select favorable subgroups, construct retrospective ROI, or change production.

This lane is hypothesis-generating only.

## Immediate Props 2.2 next lane after #468/#471

Build a **prospective capture lane before Week 3 outcomes**.

Recommended architecture:
1. Run inside or immediately after a successful `LevLine Props live refresh`, after the Props 2.1 challenger has been built.
2. Consume the exact Props 2.1 challenger records generated by that live run.
3. Apply all preregistered Props 2.2 candidates mechanically; do not select one.
4. Preserve source live-run ID, generation SHA, trigger SHA, source forecast ID/hash, forecast/data-horizon/market timestamps, kickoff, market provider/book count, role/availability state, challenger coefficients, and immutable receipt hash.
5. Preserve explicit missing-market semantics. Never backfill a market line or probability.
6. Store `outcome: null` / no grading information in the prospective receipt.
7. Keep the capture research-only and production-unauthed.
8. Evaluate only after games finalize, with the frozen grid unchanged.

Do not wire this capture against the stale #471 branch because that branch predates later live-workflow changes such as depth-chart transport. First get #468 onto main, rebuild #471 on current main, then stack capture on that current state.

## Repo cleanup policy

The earlier Props 2.0 experiment backlog was intentionally reduced. Do not reopen superseded branches merely because they contain interesting experiments. Preserve unique evidence, but use the current Props 2.1/2.2 path as the active program.

When a replacement PR is created on current main, close the stale predecessor and say which PR supersedes it.

## First actions for the next chat

1. Check run **35675981382** and verify Sunday Signal artifacts on committed main.
2. Check #468 targeted preregistration + firewall checks; merge when clean.
3. Rebuild #471 on the newly merged current main if still stale/nonmergeable.
4. Check #474 and merge if its forward-only receipt tests/firewall are clean.
5. Check #473; preserve it as diagnostic-only.
6. Stack the Props 2.2 prospective-capture lane on the current-main implementation before the next pregame capture window.
