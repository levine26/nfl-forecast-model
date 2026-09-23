# Market Microstructure Review

## Market object hierarchy

An NFL spread is not fully described by a single number. A complete quoted state can include:

- spread number on each side;
- price/juice on each side;
- sportsbook identity;
- quote timestamp;
- open/current/close horizon;
- dispersion across books;
- moneyline and total;
- movement through or around key numbers.

Phase 1 therefore distinguishes the **historical generic line benchmark** available in LevLine's current schedule data from a true timestamped, book-specific wager proposition.

## Spread number and side price

At a fixed spread, changing the juice changes the break-even probability and can encode market pressure that has not yet resulted in a half-point move. This is economically meaningful because moving a spread through an NFL key number can be discontinuous in value.

However, Phase 1 found no auditable historical spread-side price/book/timestamp field in LevLine's default historical schedule path. Therefore price-at-key hypotheses are not smuggled into Q1-Q3 using invented -110 prices.

Where actual two-sided prices are available, both sides must be retained. A paired no-vig price probability may be computed from American-odds implied probabilities by normalizing the two raw implied probabilities. That normalized object is a market-price signal, not a claim that the bookmaker has published a true probability.

## Multiple books and consensus

Multiple sportsbooks can reveal:

- consensus location;
- dispersion/uncertainty;
- stale outliers;
- price pressure at a fixed number;
- asymmetric movement through key numbers.

The attractive hypothesis is that a collection of `(line, price)` pairs can be translated through a discrete key-aware distribution into a latent fair margin. But a complex latent estimator would add material researcher degrees of freedom and requires historical price/timestamp coverage LevLine does not currently possess for the full development period.

### Phase-1 decision

A multi-book latent fair-line estimator is **not** part of historical Q1/Q2/Q3 V1. It is authorized only as a later prospective/paid-data extension after raw book-specific quotes are archived with timestamps. No outcome result may be used to choose its functional form.

## Open, current, T-120 and close

Market timing is itself information.

- Opening line: early market, lower information aggregation/liquidity in many games.
- Current line: ambiguous unless timestamp is recorded.
- T-120: a specific outcome-blind forecast horizon already supported by LevLine's prospective snapshot selector.
- Closing/late line: strong information benchmark but unavailable at an earlier decision time and therefore prohibited as an earlier feature.

Historical nflverse-style schedule fields are treated as a generic late/closing development benchmark because the current pipeline does not establish exact book/timestamp provenance. They must not be relabeled T-120.

Prospectively, T-120 is the preferred LevLine research lock when evaluating a decision intended to exist two hours before kickoff.

## Line movement

Line movement can reflect injuries, weather, liquidity, bettor information and ordinary market rebalancing. But a valid feature requires both endpoints to be point-in-time known.

Historical Q1-Q3 V1 therefore exclude line movement because the current historical schedule record lacks the needed timestamped quote path. Prospective line movement may be stored from append-only snapshots and evaluated only under a separate preregistration.

## Movement through key numbers

Crossing 3 or 7 changes wager economics because discrete NFL margin mass is concentrated there. Recent peer-reviewed work using 3/7 crossings finds strong demand discontinuities but no corresponding realized-return discontinuity. Thus crossing a key number must not be treated as automatic alpha.

Q2 instead models the consequence that matters mechanically: probability mass at the key margin and hence the difference between `-2.5`, `-3`, and `-3.5` (and analogous neighborhoods).

## Price-at-key latent information

Hypothesis: at an unchanged key-number spread, increasingly expensive favorite/underdog juice may be a latent precursor to a number move and/or contain information about the market's fair margin.

### Preregistered status

- scientifically plausible;
- historically underidentified with current free data;
- **not** a primary Phase-2 Q1-Q3 feature;
- may be evaluated prospectively or with separately acquired historical priced data;
- if evaluated, it must use only quotes timestamped before the prediction horizon and compare price information against a same-line/no-price market null;
- outcome-based choice of a juice threshold is prohibited.

## Moneyline/spread relationship

The schedule path contains home/away moneylines in addition to spread and total for relevant historical rows. When both moneylines exist, LevLine can compute a no-vig home win probability. This supplies a useful market-only shape constraint for M1/M2 because a spread and a moneyline jointly contain more distributional information than either alone.

It does **not** supply spread-side cover price.

## Spread/total relationship

Spread and total jointly summarize expected scoring environment. At a given spread, a lower total can change the relative value of each point and may alter margin dispersion/key-number mass. Phase 1 therefore admits total as a Q1/Q3 main effect and freezes one Q2 scale interaction: `abs(S) * (total - 45)`.

No broader interaction explosion is authorized.

## Liquidity and information aggregation

Public data do not reliably expose NFL betting-market liquidity at each historical book/snapshot. Liquidity is therefore not a V1 feature. The market itself is nonetheless treated as the primary information-aggregation benchmark, consistent with both academic literature and prior LevLine results.

## Stale books and dispersion

A book is only meaningfully 'stale' relative to contemporaneous alternatives. Detecting staleness requires multiple books observed at comparable timestamps. V1 historical data do not meet that contract.

Prospective multi-book collection should preserve raw quotes rather than only a consensus so future research can distinguish:

- median/consensus line;
- best available number;
- book dispersion;
- price pressure;
- stale outliers.

## Microstructure conclusion

The Phase-1 scientific decision is conservative:

- use the available historical line/total/moneyline state for Q1-Q3 development;
- model key-number economics directly through Q2;
- do not fabricate juice, movement, book dispersion or liquidity;
- archive richer book-specific priced snapshots prospectively;
- reserve latent fair-line/multi-book price inference for a later preregistered extension.

This preserves the distinction between a valid ATS formulation test and an under-sourced market-microstructure fishing expedition.