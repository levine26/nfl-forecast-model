# Sunday minimum viable operating contract — the only required deliverable

1. The live game-market **Scout** must run using latest official F-ST outputs, preserving separate ML probabilities, ATS margin probability distribution and total points probability distribution. It must not equate moneyline chance with ATS cover chance.
2. If fresh, attributable book-specific prices are present, run the quote board. Otherwise rank *model-relative* candidates but mark actionable EV and ROI unavailable. No automatic wager/positive-edge claim.
3. Show 2022–25 frozen historical ML evidence and negative ATS candidate evidence beside the watchlist as calibration warnings, not false new historical metrics.
4. Run B08A historical CSV audit **only if** the genuinely pregame historical forecast rows are available. Do not generate 2021 F-ST forecasts backward from a 2026-trained model; do not invent book prices.
5. Player TD/yardage analysis is **third-party integration only** and does not block Sunday. Use `prop-providers` matrix; authorized timestamped projections only. Do not imply Custom Venom is Jake Venom without confirmed identity.
6. Append immutable new B08/B09 receipts after each implementation, include exact tests, Git commit and CI gate. No production promotion.