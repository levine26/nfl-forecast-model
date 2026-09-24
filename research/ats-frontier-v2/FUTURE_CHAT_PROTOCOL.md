# FUTURE CHAT PROTOCOL

Every future chat continuing `LEVLINE_ATS_FRONTIER_V2` must begin by reading these files from current `main`:

1. `research/ats-frontier-v2/MASTER_PLAN.md`
2. `research/ats-frontier-v2/PHASE_STATUS.md`
3. `research/ats-frontier-v2/CURRENT_STATE_AND_NEXT_STEPS.md`
4. `research/ats-frontier-v2/DECISION_LOG.md`
5. the previous completed phase's `FINAL_PHASE*_RECEIPT.md`
6. the relevant data/scientific contract for the phase

Then verify current repository `main`, open Frontier PRs and CI before acting.

## Mandatory behavior

- Do not restart completed phases.
- Do not repeat literature review unless genuinely new evidence affects a frozen assumption.
- Do not resurrect hypotheses killed in `DECISION_LOG.md` without a formal pre-result governance amendment explaining the new evidence.
- Do not inspect completed-2026 outcomes for design/tuning.
- Do not modify production unless Phase 7 is complete and the user explicitly authorizes promotion.
- If the current phase is Phase 2, work on data qualification/PIT reconstruction only; target performance remains sealed.
- If the current phase is Phase 3, freeze architecture/evaluation before results.
- If the current phase is Phase 4, execute the frozen experiment once and preserve negative results; no rescue.

## Anti-redundancy checkpoint

Before creating any new candidate, answer from repository evidence:

1. What is the mechanism?
2. What information is genuinely new conditional on market state?
3. Which prior LevLine failure is closest to it?
4. What exactly is different enough not to repeat that failure?
5. Is required PIT data proven available?
6. What preregistered falsification would kill it?

If these cannot be answered, do not build it.