# Phase 1 Market Microstructure Review

## 1. Principle

A spread quote is a pair of economically distinct objects:

`(number, side price)`

and, in a multi-book market, also has:

`(book identity, quote/update timestamp)`.

LevLine must not collapse these fields into a single generic `spread` concept when making price-aware claims.

## 2. Posted line versus latent fair line

The line aggregates substantial public/private information and is the primary null. However, bookmaker markets are not frictionless exchanges and a posted number need not equal a literal conditional mean. The research therefore uses market state as a benchmark/anchor and tests only incremental information around it.

A multi-book latent fair margin could in principle be derived from several `(line, price)` pairs plus a margin distribution. But historical LevLine development data do not currently provide revision-safe multi-book line/price snapshots. V1 therefore **does not preregister a multi-book latent-fair-line estimator**.

Disposition: `PROSPECTIVE_EXTENSION_ONLY` unless a qualified historical source is established before a separately versioned experiment begins.

## 3. Spread juice / price

Price matters because the same -3 at -105 and -3 at -125 does not have the same break-even economics. At whole-number key lines, side price may also reflect a bookmaker's reluctance to move the number through a key margin.

This is scientifically plausible but not assumed to create a predictive edge.

Current open-source `nfelotranslation` practitioner analysis of within-spread moneyline pricing did not establish a large universal incremental signal after spread. That finding reduces the justification for making price-at-key-number a primary historical LevLine hypothesis, especially without historical spread-side price data.

V1 decision:

- exact quoted spread-side price is used whenever a source genuinely provides it;
- historical rows without side price are never assigned synthetic -110 and called quoted-price evidence;
- a standardized -110 sensitivity may be reported only as `REFERENCE_MINUS110`, clearly separate from actual-price EV/ROI.

## 4. Open, current and close

These are different information sets.

- Historical nflverse schedule market fields remain an opaque closing/late benchmark.
- LevLine's `market_t120` utility is a separate timestamp-controlled prospective/replay horizon from append-only run history.
- Opening versus closing comparisons require a source that actually preserves both horizons.

No later quote may be backfilled into an earlier decision horizon.

## 5. Price movement without number movement

This is potentially informative, especially at key numbers, but V1 historical testing is data-limited. Prospective collectors should preserve every book's price and update time so later work can distinguish:

- price-only movement;
- half-point/whole-point number movement;
- movement through 3/7/other keys;
- cross-book disagreement;
- stale versus fresh quotes.

No outcome-derived threshold for “meaningful movement” is authorized in Phase 1.

## 6. Book dispersion and consensus

A future consensus object should be constructed from same-horizon quotes only. Candidate primitives include median line, distribution of lines, median no-vig implied probabilities and book coverage count.

V1 primary experiments do not use book dispersion historically because the necessary snapshots are not available across 2022–2025.

Prospective source qualification should preserve raw constituent quotes, not only a consensus average, so stale-book and outlier audits remain possible.

## 7. Moneyline/spread relationship

Moneyline and spread encode overlapping but non-identical information about the margin distribution. Q2's market baseline may use no-vig moneyline probability when both sides are available, but it must not infer missing odds from the final game result or from a later market.

The market baseline must report whether it is:

- spread-only;
- spread + total;
- spread + total + no-vig moneyline.

## 8. Spread/total relationship

Market total is included because it can proxy expected scoring opportunity and conditional margin variance. V1 permits only fixed, football-motivated interactions:

- signed market margin × centered total;
- favorite size × centered total.

No interaction mining is allowed.

## 9. Liquidity

Public NFL liquidity is not reliably available in the current LevLine sources. Book count and quote freshness may serve as operational coverage diagnostics but are not labeled “liquidity” unless a source actually reports volume/limits.

## 10. Microstructure conclusion

Historical Phase 2 will first test whether distributional ATS modeling improves probability quality around the existing market benchmark. Price, multi-book dispersion and line-path microstructure remain important **prospective data opportunities**, not excuses to fabricate historical features.