# SELECTIVITY AND ECONOMICS CONTRACT

## Historical primary policy

**No selective betting rule is authorized in Phase 4.**

M3 and M4 are evaluated on all eligible common rows. Phase 4 may not search edge thresholds, confidence cutoffs, model-market gaps, key-number subsets, favorite/underdog subsets, top-decile rules or any other pass/bet filter.

This is intentional. The historical program first asks whether the probability model contains incremental information, not whether a mined subset can look profitable.

## ATS diagnostics

- forced side selection, if shown, is based on the higher preregistered cover probability after treating pushes explicitly;
- pushes are reported separately;
- ATS hit rate is diagnostic only;
- no candidate selection or tuning uses ATS accuracy.

## Historical economics

Where real spread-side price is present and was available at the candidate's actual prediction horizon, actual-price EV may be reported as a secondary diagnostic.

Where real side price is absent—as in the horizon-opaque historical schedule benchmark—do **not** claim actual historical ROI.

A sensitivity labeled exactly:

`REFERENCE_MINUS110`

may compute hypothetical break-even/return arithmetic at -110, but every table/figure must state that it is not a historical quoted-price profitability estimate.

## Prospective economics

M1/M2 future shadow rows may compute no-vig and actual-price EV only from prices captured before their frozen horizon. No future/closing price may be substituted for an earlier quote.

## Future selectivity

A selective betting policy, if scientifically warranted after a candidate survives proper-score validation, requires a new preregistered decision-policy version. Phase 4 cannot create one from observed historical returns.