# MARKET SAMPLE AUDIT

## Audit status

No unauthorized purchase was made. No historical paid endpoint was represented as empirically sampled when only documentation/sample schemas were available.

### The Odds API
- Public historical NFL example confirms event identity, commence time, bookmaker containers and featured markets.
- Historical timestamp semantics: closest stored snapshot equal to or earlier than requested timestamp.
- Snapshot archive: 2020-06-06 onward; 10-minute cadence initially; 5-minute cadence from September 2022.
- Historical endpoint: paid-only.
- Full NFL season × horizon × book missingness: `NOT_MEASURED__PAID_HISTORY_UNAVAILABLE`.

### SportsDataIO
- Public schema confirms sportsbook identity, Created/Updated timestamps, spread numbers, side payouts, moneylines and totals.
- Documentation distinguishes pre-game odds and line-movement behavior.
- Full historical real-data revision audit: `NOT_MEASURED__ACCESS_GATED`.

### PropLine
- Public docs confirm line-history shape and temporal semantics.
- Archive begins April 2026.
- Historical pre-2026 M1 suitability: `NO`.

## Scientific consequence

Phase 2 can freeze a valid quote schema and selection algorithm, but cannot honestly populate empirical historical M1 coverage percentages without authorized access to the paid historical records.