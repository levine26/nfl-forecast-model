# Phase 5 Failure / Correction Log

This file preserves operational failures without converting them into scientific degrees of freedom.

## 2026-09-22 — first workflow attempt stopped at pre-result contract test

- workflow: `35827845845`
- head: `9b33b2fcbdc545166c5e4056e6735ad91c3e62ae`
- failed job: `Phase 5 frozen-contract gate`
- historical Candidate 5 package: **NOT RUN**
- Candidate-5-specific metrics generated: **NO**

Cause: the synthetic winner-change unit fixture had two switched games that were both Candidate-5-only wins, but the test incorrectly asserted a 1–1 discordant split. The production research implementation correctly returned 2 Candidate-5-only wins and 0 F-ST-only wins.

Correction commit:

`b86b7c98b40a3b68e6fb4e42f9aeb6592554065a`

Correction: update only the test expectation to 2–0 and assert changed-winner accuracy 1.0. No feature, model, lambda grid, chronology, threshold, evidence boundary, 2025 policy, classification rule or production surface changed.

## First successful frozen historical execution

- workflow: `35828122187`
- triggering head: `b86b7c98b40a3b68e6fb4e42f9aeb6592554065a`
- contract gate: **SUCCESS**
- frozen historical package: **SUCCESS**
- exact-run gate: **SUCCESS**
- evidence preservation commit: `8fce0be359d93d68bc2c4bba852ede4181a38368`

This is the first Candidate-5-specific performance execution. Its negative scientific result is preserved without rescue.
