# Market independence audit

This audit is diagnostic only. It compares PURE, the vig-free market, and candidate blend families on the same historical OOS sample; measures disagreement, favorite flips, Brier score and log loss; and performs walk-forward market-weight selection using only earlier seasons. Historical nflverse prices are closing-line data, so no closing-line-optimal weight may replace the production T−120 blend. Starting in 2026, official T−120 snapshots should be used to evaluate any future production-weight change fairly.
