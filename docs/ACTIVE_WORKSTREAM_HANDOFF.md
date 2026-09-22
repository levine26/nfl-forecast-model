# Active LevLine / Sunday Signal Workstream Handoff

**Point-in-time:** 2026-09-21 evening America/Los_Angeles  
**Repository:** `levine26/nfl-forecast-model`

Always re-check current `main`, open PRs, and current workflow runs before acting.

## Sunday Signal / LevLine

Sunday Signal is the active production product. The official winner-probability path remains `F-ST-01-FROZEN-2026`.

The Week 2 editorial recovery was verified healthy before the Props reset:

- frozen weekend editorial roster: 15 games;
- game previews: 15;
- contextual evidence: 15;
- 15 unique headlines;
- media reporting: 15 trusted games;
- failed Groq games recovered through the validated ChatGPT editorial fallback;
- no recovery changed LevLine/F-ST probabilities, official picks, grading, or locks.

Continue normal Sunday Signal monitoring and production QA. Do not reopen old editorial incidents unless current committed artifacts regress.

## Props status — intentionally retired

Props is **not an active production or research workstream on main**.

The September 2026 reset deliberately:

- removed Props from the Sunday Signal UI and dashboard publication path;
- removed Props live/scheduled workflows;
- removed Props implementation/research/test code and raw artifacts from `main`;
- preserved the full pre-reset repository on `archive/props-pre-revamp-2026-09-21`;
- preserved the scientific record in `docs/props/PROPS_RESEARCH_ARCHIVE_2026-09.md`.

Do not continue Props 2.0, 2.1, or 2.2 incrementally. Do not reactivate old workflows or branches. Any next Props effort should begin as a clean-sheet successor project using the archived lessons as inputs.

## Standing non-Props research/governance issues

These remain separate from the retired Props workstream:

- #182 — reconcile F-ST historical probability metrics;
- #104 — disclosed F-ST-01 legacy freeze-provenance gap;
- #4 — validated conditional scenario engine.

Treat them according to their own governance constraints; the Props reset does not authorize changes to the official winner model.
