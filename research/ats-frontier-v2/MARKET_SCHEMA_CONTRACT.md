# MARKET SCHEMA CONTRACT

## Canonical quote table

Required fields:

- `provider`
- `provider_event_id`
- `canonical_game_id`
- `bookmaker`
- `market`
- `side`
- `line`
- `price`
- `quote_timestamp_utc`
- `kickoff_timestamp_utc`
- `minutes_to_kick`
- `ingestion_timestamp_utc`
- `source_revision_id` (nullable only when provider does not expose one)
- `raw_payload_ref` or preserved raw source fields

Bookmaker identity and price must not be flattened away.

## Horizon reconstruction

For target horizon `h` minutes:

`target = kickoff_timestamp_utc - h`

Select, separately by provider/book/market/side, the quote with maximum `quote_timestamp_utc` such that `quote_timestamp_utc <= target`.

The selector must never choose a quote after `target`; nearest-neighbor matching is prohibited unless it is constrained to at-or-before.

`latest_pre_kick` means the latest quote with `quote_timestamp_utc <= kickoff_timestamp_utc` and must exclude post-kick updates.

## Derived outcome-blind market state permitted later

Consensus median/mean, dispersion, active-book count, quote age, price-implied side probability, book-to-consensus deviation, fixed-lookback movement, movement breadth/direction, leader/follower timestamps, price-only movement, key-number crossings, spread/moneyline consistency, and total/spread state may be constructed only from PIT-valid quotes.