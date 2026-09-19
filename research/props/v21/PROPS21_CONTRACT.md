# Props 2.1 Sunday Challenger contract

`levline-props-2.1-sunday-v0.1` is a new research challenger. It reads frozen V1 football distributions, qualified current reporting, and timestamped sportsbook state. It does not mutate published V1, Market Anchor, Shadow A, Shadow B, or F-ST.

The challenger produces:

- a structured player role state with accepted and rejected evidence;
- a read-only xTD diagnostic and a separately testable pre-2026 context-model interface;
- a market distribution when observed thresholds support one, with explicit consensus fallback otherwise;
- fail-closed QA, uncertainty limitations, and reason tags;
- a separate public JSON document and append-only prospective receipt stream.

`RADAR`, `WATCH`, and `NO SIGNAL` are research presentation states. They are not wager recommendations or validated edge thresholds. Blocked numerical rows are suppressed. A started or partial slate cannot replace the last valid publication.

Current live numeric forecasts inherit the V1 simulator distribution. The context-fitted xTD mechanism is inactive until qualified pre-2026 context training and pregame projected opportunity contexts are available. That limitation is retained in every affected record.

Every receipt records the source V1 forecast ID, source artifact hash, player/game identity, forecast and kickoff times, Pure LevLine outputs, market line/probability/state hash, role state, xTD status, QA state, version, and immutable/no-production flags. It contains no outcome at capture time.
