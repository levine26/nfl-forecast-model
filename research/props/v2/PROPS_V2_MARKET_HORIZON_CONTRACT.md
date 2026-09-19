# Props 2.0 Market Horizon Selection Contract

Status: **PREREGISTERED BEFORE 2026 MARKET/OUTCOME EVALUATION**  
Version: `levline-props-v2-market-horizons-v0.1.0`

## Purpose

Map the exact timestamped captures preserved by the Props market archive into fixed research horizons
without using game outcomes, later market movement, or betting performance to choose the windows.

## Frozen horizons

| Horizon | Target | Maximum timing error |
|---|---:|---:|
| T48H | 2,880 min | ±480 min |
| T24H | 1,440 min | ±360 min |
| T12H | 720 min | ±240 min |
| T6H | 360 min | ±120 min |
| T90M | 90 min | ±30 min |
| T30M | 30 min | ±15 min |
| NEAR_CLOSE_OBSERVED | nearest capture to kickoff | capture must be ≤10 min pregame |

The broad early tolerances reflect the existing low-frequency live Props publication cadence; the
near-kickoff tolerances are narrower because market microstructure changes faster close to kickoff.
These windows are frozen before grading and may not be changed because a different window backtests
better.

## OPEN terminology

The first archived state is labeled **EARLIEST_OBSERVED**, not OPEN.

It may be called sportsbook OPEN only when the underlying source independently establishes that the
quote is genuinely the opening market. Merely being LevLine's first observation is insufficient.

## Deterministic selection

For a fixed horizon:
1. consider only strictly pregame captures within the frozen tolerance;
2. choose minimum absolute timing error;
3. break ties toward the earlier capture;
4. break any remaining tie by timestamp.

Missing horizons remain missing. No interpolation or reconstruction is allowed.

## Close terminology

`NEAR_CLOSE_OBSERVED` is a timestamped proxy useful for prospective price-discovery research. It is
not claimed to be the sportsbook's official closing line unless a qualified source explicitly marks
it as closing.

## Future evaluation

Horizon-selected states may later support:
- cross-book consensus/dispersion;
- line and price movement;
- staleness;
- same-book leader/follower analysis;
- LevLine disagreement versus subsequent movement;
- CLV using a separately qualified close.

No horizon may be chosen or discarded because of 2026 results.
