# FEATURE AND INPUT CONTRACT

This contract freezes the admissible information channels before Phase-4 target results exist.

## M3 historical inputs

Allowed:

- prior completed-game offensive EPA/play;
- prior completed-game defensive EPA/play allowed;
- prior completed-game QB EPA/dropback;
- prior completed-game offense/defense success rate as fixed secondary measurement channels;
- static team identity normalization;
- prior-only QB identity/state when known from qualified historical records;
- historical nflverse schedule spread as a market benchmark, permanently labeled exact-horizon opaque.

Forbidden:

- target-game PBP;
- target-game snaps;
- eventual target-game starter identity used retrospectively;
- same-week final inactive lists;
- broad injury features;
- target-selected matchup interactions;
- realized target-game weather.

## M4 historical inputs

Allowed:

- historical market spread transformed to home-margin sign;
- historical total line;
- observed final margin as the training target only after that row enters the historical training set chronologically;
- no team/player feature family.

M4 conditional scale is limited to `log(total/45)` and `abs(spread)/7`. Key-mass structure is limited to margin 0 and absolute margins 3 and 7.

## M1 prospective inputs

Frozen compact fields at or before T-120:

- consensus spread median;
- spread-side price/no-vig probability;
- moneyline/no-vig probability;
- total;
- spread dispersion;
- active-book breadth;
- quote age and stale-book share;
- T-360→T-120 spread movement;
- price-only movement at unchanged spread;
- movement breadth;
- crossing of 3/7;
- spread-moneyline consistency residual.

No T-60/T-30/latest-pre-kick observation may enter a T-120 prediction.

## M2 prospective inputs

Only:

- prior-only QB ability;
- T-120 starter probability from timestamped evidence;
- expected role probability;
- timestamped replacement identity;
- prior-only replacement quality;
- information-arrival timestamp;
- contemporaneous market level/movement;
- explicit source conflict/missingness.

## Canonical market quote fields

Any exact-horizon market source must retain:

- provider;
- provider_event_id;
- canonical_game_id;
- bookmaker;
- market;
- side;
- line;
- price;
- quote_timestamp_utc;
- kickoff_timestamp_utc;
- minutes_to_kick;
- ingestion_timestamp_utc;
- revision ID when exposed;
- raw payload reference/hash.

Bookmaker identity and price may never be flattened away before qualification.