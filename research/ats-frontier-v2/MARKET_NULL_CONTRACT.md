# MARKET NULL CONTRACT

The sportsbook is the primary benchmark. Every candidate comparison is paired on exact common rows.

## M1 prospective null

`M1-NULL-STATIC-T120-01`

Same T-120 market level, spread prices/no-vig probability, moneyline and total, but no path, dispersion, stale-book or breadth features. This null is evaluated at the same quote horizon and source universe as M1.

## M2 prospective null

`M2-NULL-MARKET-T120-01`

Same T-120 market state without QB expected-value-delta features.

## M3 historical null

`M3-NULL-MARKET-NORMAL-01`

- historical nflverse schedule market center under the explicit horizon-opaque label;
- prior-only constant Normal residual scale estimated with the same chronology as the candidate;
- integer-bin cover/push/loss translation;
- no football-state correction.

M3 and this null share the identical distributional translator. Only `delta_football` differs.

## M4 historical null

`M4-NULL-STUDENTT-CONSTANT-01`

- identical market center;
- tail-safe Student-t integer-bin PMF;
- chronology-clean selection of `nu` from `{4,6,10,30}`;
- prior-only constant scale;
- no conditional-scale terms;
- no 0/3/7 key-mass offsets.

## Prohibited weak baselines

Do not substitute:

- 50% ATS coin flip as the main proper-score null;
- a generic team-strength model;
- an opener when the candidate uses a later market state;
- a market line from a different horizon/source population;
- a Gaussian null for M4 if the preregistered Student-t null is available.

Coin-flip ATS intervals may be reported only as descriptive diagnostics.