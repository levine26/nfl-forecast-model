# LevLine Props 2.0 — Data Source Audit

Status: **LIVING AUDIT**

| Source / surface | Coverage / use | Point-in-time quality | Live availability | Main limitation | Disposition |
|---|---|---|---|---|---|
| Frozen V1 Action Network OPEN receipts | 2023–2025 Props evaluation | Genuine OPEN population with frozen hashes | Historical only | Already inspected; development evidence | Canonical retrospective benchmark |
| Live Props The Odds API adapter | Current player props | Timestamped capture | Yes with credential | Current capture is not yet full multi-horizon historical market state | Retain; add research horizon state |
| LevLine market-capture v2 | T−120/T−60/T−45/T−30 multi-book game markets | Strong PIT; provider IDs, request times, book timestamps | Yes | Built for game markets, not player props | Reuse patterns/contracts, not data semantics |
| LevLine market-state v1 | Movement/dispersion derivatives | Strong PIT, retries resolved by closest target | Yes | Game-market scope | Reuse implementation pattern for Props |
| nflverse play-by-play | PBP back to 1999 | Historical event chronology | Yes/reproducible | Release timing differs from true live tracking | Core football history |
| nflverse / repository participation & snap sources | Lagged role state | Historical; target week excluded | Repository-supported | Snap share is not route participation | Valid proxy with explicit source quality |
| FTN charting integration | Historical/live-capable matchup state | Strictly lagged in experiment; exact historical publication timestamps not claimed | Source-dependent | Prior residual experiment was null | Preserve state as possible mechanism input, not generic residual |
| NGS public metrics / methodology | Expected rushing, completion, tracking concepts | Public aggregate/metric dependent | Limited public live fields | Raw tracking generally unavailable | Architectural inspiration + available fields only |
| Injury/practice/depth-chart state | Availability mixtures | Must be source-qualified and timestamped | Partial | Historical workload labels may be incomplete | Prospective capture if reconstruction is not defensible |
| Weather | Outdoor environment | Timestamped forecast required | Yes where source-qualified | Small/conditional effect; venue resolution required | Use only after standalone justification |

## Current source-quality rules

1. Provider timestamp is not assumed equivalent to information-publication timestamp.
2. Retrospectively downloaded data are not automatically considered historically available live.
3. Any source lacking a credible pregame chronology is limited to retrospective mechanism research.
4. Stable player/game identifiers are mandatory; fuzzy identity joins fail closed.
5. Missing source evidence is preserved as missingness rather than silently imputed from future rows.

## External source notes

nflverse documents play-by-play availability back to 1999 and explicitly notes that underlying NFL
data remain subject to their owners' terms of use. NFL Next Gen Stats describes tracking data as
location/speed/distance/acceleration sampled 10 times per second and used for route detection,
Completion Probability and Expected Rushing Yards. Public NGS methodology is therefore valuable for
mechanistic model design, but does not imply LevLine has access to raw tracking feeds.

## Highest-value data gaps

- timestamped **multi-book player-prop** histories at several pre-kickoff horizons;
- reliable route participation / routes-per-dropback state;
- historical point-in-time injury/practice/depth-chart evidence sufficient to label limited workloads;
- target-depth / air-yard and YAC decomposition with live-compatible provenance;
- closing player-prop price/line captures for CLV.

Paid historical data are blockers unless credentials/licensing are actually available. The program
must not assume access.
