# LevLine production: forecast-only operation (October 11, 2026)

**Decision:** Retire matchup Reads and autonomous editorial/source-review pipelines. Sunday Signal publishes numeric LevLine forecasts, market comparisons, forecast movement, model diagnostics, immutable history, and lock-accountability artifacts. No human/AI story is part of the public forecast contract.

## Production isolation

- `write_outputs` no longer requires `game_previews.json`, provider quotas, narrative synthesis or source-verification receipts. Legacy Read reconstruction is opt-in for offline regression testing only.
- GitHub Pages does not include the game-preview or editorial-acceptance JSON and cannot fail a deployment because editorial prose differs from the model.
- Groq/ChatGPT/contextual editorial workflows have manual-only historical entrypoints; they have no push, workflow-run or scheduled self-activation. No normal forecast or lock run spends money on editorial providers.
- Do not mutate historical `outputs/prediction_history.csv` receipts, the frozen official F-ST model or research-only candidate files.

## Operating priority

1. **P0 locks:** Effective 2026 Week 6, target T-60 per game; prior weeks retain their actual T-120 rules. Grade *real receipt timestamps* against the target. Report late/missing games; never backdate.
2. **P0 external reliability:** GitHub Actions cron is best effort. The external watcher kit under `ops/offgithub-lock-watch/` is **not deployed** without an external account, dispatch credential, alert endpoint, KV configuration and independent health probe. Green CI does not establish a T-60 SLA.
3. **P1 model integrity:** One frozen F-ST canonical probability, vig-free market comparison, separate ATS diagnostics and append-only official lock receipts.
4. **P1 measured improvements:** Leakage-safe chronological research and prospective challenger comparisons, without promoting any research model without explicit approval.

**Acceptance:** All current-slate games have accurate pre-deadline immutable receipts; an independent live dispatch and alert has been demonstrated; displayed public probabilities exactly agree with receipts; and model research remains independently validated. These are not yet proven merely by this feature removal.
