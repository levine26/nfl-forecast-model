# Sunday Signal Bet Tracker contract

The Bet Tracker is a presentation/accountability feature only. It never feeds betting outcomes, ROI, or sportsbook prices back into LevLine forecasting.

- Unit size: $25 risked per wager.
- Moneyline: one unit on every immutable LevLine ML pick, settled at a sportsbook price verified to match the market probability stored at the LevLine lock receipt.
- Spread: one unit on every immutable LevLine modeled spread, not the market spread. Captured side juice is used when genuinely stored at lock; otherwise the approved -110 fallback is used.
- Pushes: $0 P/L, stake returned, and the $25 risk remains in the ROI denominator.
- Track Record: the History page leads with only cumulative 2026 Moneyline and LevLine Spread record + ROI cards. It does not lead with risked dollars, combined season P/L, or a week selector. Pending wagers do not enter the historical record or ROI.
- This Week: the current public slate is shown game by game. Each row/card shows the LevLine ML pick, LevLine modeled spread, HIT/MISS/PUSH/PENDING state, and combined game P/L once both wagers are settled.
- Current pre-lock games may appear in This Week before an immutable receipt exists. They are labeled Awaiting Lock and never receive synthetic sportsbook odds or hypothetical P/L.
- Week totals: Moneyline and LevLine Spread each report record, P/L, and ROI for settled wagers; the section also reports combined weekly P/L and ROI. Pending wagers are excluded until graded.
- Historical integrity: missing winning ML price data fails closed. The tracker never substitutes LevLine fair odds, a later market, or a reconstructed synthetic sportsbook price.
- Historical backfill: archived nflverse snapshots may be used only when the raw moneyline pair reproduces the immutable receipt's vig-free market probability within the strict verification tolerance.

- Season trajectory: a compact cumulative P/L-by-week chart may visualize Moneyline and LevLine Spread history, but it must stop/fail closed for a series once verified profit becomes unavailable.
