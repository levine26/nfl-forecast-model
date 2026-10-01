# ChatGPT-primary Sunday Signal editorial path

## Production authority

Sunday Signal HUMAN editorial content is produced from the ChatGPT current bundle under `inputs/chatgpt_media/current/`.

The production numerical forecast remains `F-ST-01-FROZEN-2026`. This migration does not change model features, probabilities, grading, locks, expected-margin diagnostics, or the canonical public-forecast bridge.

## Runtime

1. Contextual intelligence refreshes reporting/evidence.
2. ChatGPT refreshes only stale, contradicted, or missing HUMAN-layer game payloads using current direct reporting.
3. The complete current bundle remains present for the full 16-game slate.
4. `Sunday Signal ChatGPT primary editorial ingestion` performs focused validation, composition, deterministic LevLine paragraph rendering, full-slate validation, and atomic publication.
5. A failed ChatGPT refresh retains the last validated HUMAN Read for that game unless the existing copy is factually unsafe.

## Groq retirement

Automatic Groq dispatch and scheduled/push production runs are disabled. The legacy Groq writer remains manual-only as an explicit rollback mechanism and is not a production authority.

Legacy `groq_provider_fallback` status is historical compatibility data after this migration and must not be used as the current production-health gate. Production health is determined by the validated ChatGPT current bundle, full-slate validator, deterministic paragraph-2 renderer, canonical forecast provenance, and live deployment.

## Safety properties

- ChatGPT editorial content cannot change LevLine probabilities.
- Paragraph 2 is regenerated from the latest canonical prediction row.
- Existing validated HUMAN prose survives unrelated context refreshes.
- Refresh failure is game-scoped.
- Publication remains fail-closed on focused/full-slate/source/uniqueness/pick validation.
