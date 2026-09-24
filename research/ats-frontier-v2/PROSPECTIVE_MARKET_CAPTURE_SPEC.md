# PROSPECTIVE MARKET CAPTURE SPEC

The purpose is to prevent another historical market-state data failure. This is infrastructure specification, not prospective validation and not authorization to purchase data.

## Primary provider contract

Preferred provider: The Odds API current NFL game markets when legally/account-accessible under the user's existing or future authorized plan.

Required markets:

- spreads with side prices;
- h2h / moneyline;
- totals.

Preserve all returned bookmaker identities. Do not reduce to a consensus before raw retention.

A secondary current public source may be captured for corroboration, but it may not be silently merged as though provider timestamps/semantics were identical.

## Cadence

For every scheduled NFL game, ensure explicit capture attempts at each frozen horizon and maintain the following minimum background cadence:

- T-2160 to T-720: every 60 minutes;
- T-720 to T-360: every 30 minutes;
- T-360 to T-120: every 15 minutes;
- T-120 to kickoff: every 5 minutes;
- explicit scheduled attempts at T-2160, T-720, T-360, T-120, T-60 and T-30;
- one final pre-kick attempt targeted within the last 5 minutes, never after kickoff.

If provider quota does not support this cadence, reduce breadth only through a documented pre-season governance amendment. Do not silently thin captures after seeing outcomes.

## Immutable raw record

For every response retain, privately where licensing requires:

- provider;
- request timestamp;
- provider response timestamp;
- ingestion timestamp;
- event/provider ID;
- canonical game ID;
- scheduled kickoff timestamp as known then;
- bookmaker key/title;
- market;
- side/outcome;
- line/point;
- price;
- bookmaker last-update timestamp when exposed;
- raw payload or immutable object-store reference;
- SHA-256 of exact raw payload;
- HTTP status/provider error class;
- collector version/commit SHA.

Append only. Never overwrite an older raw payload with a corrected/new response.

## Retry behavior

For a scheduled capture failure:

1. retry after approximately 15 seconds;
2. retry after approximately 45 seconds;
3. retry after approximately 120 seconds;
4. record `CAPTURE_FAILED` if still unsuccessful.

A later quote may not be backfilled into the failed earlier horizon. The missing horizon remains missing.

Rate-limit responses are logged distinctly from network/provider failures.

## Kickoff handling

Use authoritative scheduled kickoff as known at capture time and preserve schedule revisions. If kickoff changes, retain both the previous scheduled time and revision timestamp. Eligibility is evaluated against the schedule state known when the capture occurred, with a later reconciliation field for the actual official kickoff; no quote at/after actual kickoff may be admitted as pregame.

## Canonicalization

Maintain versioned maps for:

- team aliases;
- bookmaker aliases/renames;
- provider market/outcome naming;
- event-to-canonical-game join.

Never collapse multiple books into one before the raw layer.

## Rights / redistribution

Raw public visibility is not assumed to grant redistribution rights. Default third-party raw payloads to `NO_REDISTRIBUTION_ASSUMED` / private storage unless the provider license explicitly permits redistribution. Repository artifacts should contain schemas, hashes, coverage summaries and derived research tables only as rights permit.

## Coverage monitor

Before each game, compute outcome-blind capture health:

- books active by market/horizon;
- line + price completeness;
- h2h completeness;
- total completeness;
- quote age;
- stale-book share;
- missing scheduled captures;
- provider conflicts.

Coverage alerts may repair future collection infrastructure but may not alter a frozen prediction with a future quote.

## Outcome firewall

The collector never reads game results. Capture/storage is independent from grading. Completed-2026 outcomes may not be used to redesign the historical Phase-3 architecture.