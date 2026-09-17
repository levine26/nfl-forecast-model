# LevLine Props Market Contract

Status: research beta interface
Lane: research/props-market
Schema version: levline.props.market.v1

## Purpose

This contract is the sportsbook benchmark layer for offensive player props. It does not
alter official LevLine winner probabilities and it does not label a model disagreement as
a betting recommendation.

All prospective artifacts are point-in-time. Quotes captured after the artifact as-of time
are excluded. Quotes marked as closing are evaluation-only and are excluded from live
consensus, movement, best-price, and market-CDF calculations.

## Supported normalized prop types

- passing_yards
- rushing_yards
- receiving_yards
- receptions
- passing_tds
- rushing_tds
- receiving_tds
- anytime_td

Position eligibility is enforced by the upstream player/simulation lanes. The market layer
preserves position, team, opponent, game_id, and stable player_id when supplied.

## Quote schema

The canonical Python schema is nfl_forecast.props_market.PropMarketQuote.

Identity/provenance fields:

- schema_version
- provider
- sportsbook_key
- sportsbook_title
- captured_at_utc
- sportsbook_last_update_utc
- provider_event_id
- provider_market_key
- game_id
- player_id
- player
- team
- opponent
- position
- prop_type
- related_market_group_id
- cross_market_join_key

Price/threshold fields:

- line
- over_american / under_american
- yes_american / no_american
- decimal equivalents
- raw implied probabilities
- no-vig probabilities when a genuine opposing price exists
- overround
- devig_method
- is_alternative_line
- is_closing

One-sided anytime-TD quotes retain raw implied probability. They do not receive a fabricated
no-vig probability. A binary no-vig probability is emitted only when both Yes and No prices
are actually observed.

## Odds and vig removal

Utilities support:

- American to decimal
- decimal to American
- decimal to implied probability
- American to raw implied probability
- probability to fair decimal/American odds
- two-way proportional de-vig
- two-way additive de-vig
- two-way power de-vig

The default live contract is proportional de-vig. The chosen method is explicit in every
derived record so methods cannot be silently mixed.

## Consensus

Consensus line is the median of the latest unambiguous primary line from each sportsbook
at or before as_of_utc.

No-vig probability at the consensus threshold is derived from like-for-like thresholds.
When alternative lines are available, the engine reconstructs an approximate sportsbook
survival function P(stat > x), aggregates each threshold in logit space, projects the
curve to be non-increasing, and interpolates only inside observed threshold support.

The engine does not average Over probabilities quoted at different thresholds as though
they were the same market.

Book dispersion includes line min, max, range, and population standard deviation.

Every aggregate artifact also exposes market_data_quality with an explicit state, primary
sportsbook count, survival-threshold count, whether a two-way no-vig comparison is available,
and whether a primary consensus line exists.

## Best price

Best available price is selected by decimal payout at the exact requested threshold.
A superior price at a different threshold is not treated as a like-for-like best price.

## Movement and closing data

Movement is computed only from timestamped primary snapshots observed by the requested
as-of time. It preserves per-book opening/current thresholds and prices plus consensus
line movement. Price movement in decimal odds and raw-implied-probability points is emitted
only when the opening and current threshold is unchanged; otherwise price movement is
explicitly non-comparable rather than mixing a line move with a price move.

Closing quotes may be attached only through the explicit closing_evaluation surface.
That object is tagged evaluation_only=true. It is never used as a pregame feature.
build_market_artifact requires a separate explicit evaluation_as_of_utc whenever closing
evaluation is requested, and only closing observations available by that evaluation horizon
are attached. It preserves the individual closing-book records plus best observed closing
Over/Under or Yes/No prices when those prices are comparable at the reported closing
threshold.

Threshold CLV is side-aware:

- Over: closing line minus captured line
- Under: captured line minus closing line

Positive threshold CLV therefore means the captured line beat the eventual close for the
specified side. Same-threshold price CLV is separately available in decimal-odds units;
positive means the captured price paid more than the closing price for the identical outcome
and threshold.

## The Odds API adapter

nfl_forecast.props_market_odds_api.ingest_odds_api_event normalizes event-odds payloads.

Default recognized market keys:

- player_pass_yds
- player_rush_yds
- player_reception_yds
- player_receptions
- player_pass_tds
- player_rush_tds
- player_reception_tds
- player_anytime_td

Keys with the suffix _alternate are mapped to the same normalized prop and marked as
alternative lines when the base key is supported.

The adapter requires a caller-supplied player_id_resolver. If a provider player name cannot
be resolved to a stable ID, the row is rejected. No synthetic player identifier is created.
Unsupported provider market keys are reported as ignored rather than silently expanding
scope.

## Downstream integration

Simulation/product lanes should consume build_market_artifact output. For yardage/reception
markets the relevant fields are:

- consensus_line
- consensus_no_vig_p_over
- consensus_no_vig_p_under
- line dispersion
- individual_books
- alternative_line_survival
- best_over_price
- best_under_price
- movement
- market_data_quality
- closing_evaluation only for post-hoc evaluation

For binary TD markets use:

- consensus_no_vig_probability when a two-way Yes/No market exists
- best_yes_price
- individual book raw implied probability when the market is one-sided

Use compare_levline_to_market to produce:

- LevLine Fair Line minus Market Line
- LevLine P(Over) minus Market no-vig P(Over)
- LevLine P(Under) minus Market no-vig P(Under)
- LevLine fair odds
- best observed sportsbook price

The comparison intentionally returns bet_recommendation=null. A model/market disagreement
is evidence for evaluation, not an automatic bet label.

## Cross-market extensibility

Every record contains game_id, player_id, prop_type and cross_market_join_key. Optional
related_market_group_id can bind player markets to a team offensive context. This is enough
for the integration lane to later audit relationships such as QB passing yards versus
receiver yards, passing TDs versus receiving TDs, and team rushing context versus player
rushing markets without changing the quote schema.

## Integration steps

1. Merge this branch into research/props-integration, not directly into production logic.
2. Feed stable player IDs from the props-data lane into the Odds API player_id_resolver.
3. Preserve every raw timestamped quote before building a consensus artifact.
4. Build one market artifact per game_id/player_id/prop_type/as-of horizon.
5. Join the simulation output only after the market artifact has been frozen.
6. Store the exact artifact used in each prospective forecast.
7. Attach closing_evaluation only after it becomes legitimately observable.
8. Keep official F-ST/LevLine winner probabilities untouched.
