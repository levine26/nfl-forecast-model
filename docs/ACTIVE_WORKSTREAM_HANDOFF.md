# Active LevLine / Sunday Signal Workstream Handoff

**Point-in-time:** 2026-09-21 evening America/Los_Angeles  
**Repository:** `levine26/nfl-forecast-model`

This is the cross-chat continuity source. Always re-check current `main`, open PRs, and current workflow runs before acting. Do not restart completed work or revive superseded PRs by default.

## Non-negotiable governance

- Do not modify the official LevLine/F-ST winner model while working Props/editorial research lanes.
- Do not weaken chronology, locking, research firewalls, immutable receipt rules, or launch gates to make CI pass.
- Frozen Props 2.1 Week 2 outcomes are evaluation/diagnostic evidence only. They may motivate hypotheses but may not fit coefficients, choose weights retrospectively, tune thresholds, or construct retrospective betting signals.
- Props 2.2 is future-holdout only. Week 2 receipts must never be backfilled into its prospective ledger.
- A post-kickoff live Props no-op is a valid lifecycle state. It must preserve the last valid publication and must not create fake prospective receipts.

## Sunday Signal — verified healthy

The post-kickoff editorial collapse is repaired on committed `main`.

Key merged fixes include:
- #450 canonical locked-slate bridge;
- #455 persisted weekend editorial roster;
- #456 challenger-output race isolation;
- #465 last launch-grade full-slate recovery;
- #476 docs-only recovery race allowance;
- #480 full ChatGPT-ingestion / failed-game-fallback namespace isolation;
- #483 isolated six-game fallback retry;
- #485 code-only full-ingestion pushes validate without republishing stale bundles.

Verified on current committed `main`:
- frozen Week 2 weekend roster: **15 games**;
- `outputs/copilot_media_reads.json`: **15 games**;
- `outputs/game_previews.json`: **15 games**;
- `outputs/contextual_evidence.json`: **15 games**;
- editorial finalizer: **healthy, 15 games, 15 unique headlines**;
- provider: **healthy, 15/15 applied**;
- media reporting: **healthy, 15 trusted games**;
- Groq fallback status: **healthy**;
- every previously failed Groq game has `requires_chatgpt_refresh=false`;
- the six late unresolved games were recovered through validated ChatGPT fallback;
- recovery reused a launch-grade historical editorial snapshot and never altered LevLine/F-ST probabilities, picks, grading, or locks.

Do not reopen the one-game collapse investigation unless current committed artifacts regress.

## Props 2.1 — frozen evidence

Canonical prospective cohort:
- live workflow: `35477049179`;
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`;
- receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`;
- **3,439** frozen forecasts across **15 games**;
- retrospective forecast mutation: forbidden.

Canonical evaluation was merged in #466.

Observed Week 2 evaluation:
- **1,606** forecasts graded across 14 finalized games;
- **359** like-for-like market-matched forecasts;
- Fair-Line minus original-market MAE delta: about **+1.375**, game-clustered 95% CI roughly **[+0.828, +2.001]**;
- model-minus-market Brier delta: about **+0.0243**, CI roughly **[+0.0066, +0.0414]**;
- model-minus-market log-loss delta: about **+0.1035**, CI roughly **[+0.0432, +0.1729]**;
- preregistered probability bins showed systematic model overconfidence;
- zero original `MODEL EDGE` observations, therefore betting ROI is not measurable.

Interpretation: Week 2 did not show incremental accuracy beyond the point-in-time market. This is a diagnosis/development cohort, not a valid tuning/validation loop.

## Props work already merged

Do not redo:
- #434 — full eligible-roster concentration semantics;
- #446 — point-in-time depth-chart transport;
- #459 — fully-started target week becomes a clean live no-op;
- #466 — canonical Props 2.1 prospective evaluation;
- #478 — Props 2.2 future-holdout preregistration;
- #479 — locked Week 2 descriptive miss diagnostics;
- #481 — forward distribution-evidence preservation in new 2.1 receipts;
- #482 — deterministic Props 2.2 market-residual transformations;
- #486 — immutable Props 2.2 prospective capture contract;
- #487 — distribution-evidence evaluator;
- #488 — personnel/opportunity evidence coverage audit;
- #491 — live integration that captures Props 2.2 receipts after successful **pregame** Props 2.1 runs.

### Frozen Props 2.2 design

The preregistered grid includes:
- `P21_BASE` control;
- line-residual 25% / 50%;
- probability-residual 25% / 50%;
- fixed probability shrink-to-half diagnostic;
- combined 25% / 50% primary challengers.

Only the two combined challengers are promotion eligible.

No promotion/model-selection claim before at least:
- 3 future weeks;
- 30 finalized games;
- 1,000 market-matched observations;
- 250 observations for a prop-family superiority claim;
- clean chronology and receipt integrity;
- game-clustered uncertainty;
- multiplicity control across promotion candidates;
- no material Brier/log-loss degradation.

## Props 2.2 prospective capture — current state

The capture machinery is live, but **no Props 2.2 prospective ledger exists yet on main**. That is expected.

Reason:
- #491 merged after Week 2 was already fully started;
- every subsequent live Props source run has therefore taken the valid post-kickoff no-op path;
- the no-op path exits before creating 2.2 receipts, which preserves chronology and prevents retrospective Week 2 backfill.

The first future successful **pregame** live Props run is the real acceptance test.

That run must:
1. build a valid current-run Props 2.1 challenger artifact;
2. preserve source live-run ID, generation SHA, trigger SHA, timestamps, market provenance, and source forecast hashes;
3. apply the entire frozen Props 2.2 challenger grid mechanically;
4. append immutable/idempotent records under `challenger_outputs/props22/`;
5. reject any source receipt earlier than the frozen Props 2.2 prospective start boundary;
6. contain no outcomes or grading fields;
7. leave production Props labels and the LevLine winner model untouched.

Do not manually backfill Week 2 into Props 2.2.

## Active engineering cleanup

### #492 — legacy Props 2.0 listeners must honor live post-kickoff no-op

This is the only active workflow-noise fix at this handoff.

Problem:
- #459 made a fully-started target week a successful live no-op;
- four legacy Props 2.0 listeners still assumed every successful live refresh contains a full pregame artifact;
- they therefore produced false-red workflow failures after valid no-op runs.

#492 changes the four listeners to classify the exact source artifact:
- exactly one `levline-props-postkickoff-noop-v0.1` marker, zero other files, zero pregame game IDs, at least one started game -> clean success and skip capture;
- normal full pregame artifact -> existing provenance/SHA validation and capture behavior unchanged;
- mixed/malformed/unexpected artifact -> fail closed.

Merge #492 only after all four focused workflow PR checks pass.

## Why the latest legacy shadow failures are not model failures

The red runs from the latest successful live Props refresh did **not** fail due to forecasting, market, depth-chart, or 2.2 logic.

The exact live artifact contained only:

`postkickoff_noop.json`

with:
- contract `levline-props-postkickoff-noop-v0.1`;
- zero pregame games;
- all 16 Week 2 games already started.

The old listeners failed because they demanded `source_provenance.json`, `forecasts.json`, `manifest_slate.json`, and `market.json` even when no pregame capture should exist.

## Next-chat first actions

1. Read this file and `research/props/v21/CURRENT_STATE_AND_NEXT_STEPS.md`.
2. Check #492. If its four listener tests are green and it remains current-main/mergeable, merge it.
3. Verify Sunday Signal remains 15/15 healthy, but keep that lane monitoring-only unless it regresses.
4. Do **not** run new Week 2 tuning or weight selection.
5. Before the next untouched pregame slate, verify `LevLine Props live refresh` is green and the Props 2.2 capture hook is still wired.
6. On the first future pregame live run, verify `challenger_outputs/props22/` is created with valid immutable receipts.
7. Preserve forward personnel/opportunity and distribution evidence concurrently.
8. Do not select a Props 2.2 winner mid-holdout. Wait for the preregistered terminal evidence threshold.
9. If a PR becomes stale after main advances, create one clean current-main replacement and close the stale predecessor explicitly.

## Repo hygiene

Historical Props 2.0 / 2.1 experimental PRs were intentionally consolidated and closed. Do not reopen them merely because they contain interesting experiments.

Current scientific path:
**Props 2.1 frozen baseline -> Props 2.2 preregistered challengers -> future untouched prospective receipts -> terminal paired evaluation vs original market.**
