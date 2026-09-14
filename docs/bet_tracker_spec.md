# Sunday Signal Bet Tracker contract

The Bet Tracker is a presentation/accountability feature only. It never feeds betting outcomes, ROI, or sportsbook prices back into LevLine forecasting.

- Unit size: $25 risked per wager.
- Moneyline: one unit on every immutable LevLine ML pick, settled at a sportsbook price verified to match the market probability stored at the LevLine lock receipt.
- Spread: one unit on every immutable LevLine modeled spread, not the market spread. Captured side juice is used when genuinely stored at lock; otherwise the approved -110 fallback is used.
- Pushes: $0 P/L, stake returned, and the $25 risk remains in the ROI denominator.
- Weekly reporting: ML and LevLine Spread remain distinct and each reports record, dollars risked, P/L, and ROI.
- Season reporting: cumulative ML, LevLine Spread, and Combined P/L/ROI.
- Historical integrity: missing winning ML price data fails closed. The tracker never substitutes LevLine fair odds, a later market, or a reconstructed synthetic sportsbook price.
- Historical backfill: archived nflverse snapshots may be used only when the raw moneyline pair reproduces the immutable receipt's vig-free market probability within the strict verification tolerance.
