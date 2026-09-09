# External market-regression references

Sunday Signal's market audit is informed by public NFL forecasting approaches beyond the SuJaR baseline. In particular, nfelo treats market regression as a dynamic accuracy-versus-alpha problem rather than a fixed assumption: small model/market disagreements can be collapsed toward market, extreme opinions can be capped, and open-to-close movement can alter the amount of regression. Sunday Signal will measure these ideas on held-out historical data, but will not adopt a new production rule from 2026 outcomes or from closing-line optimization alone.

Candidate families evaluated by the audit:

- fixed linear probability blends, including the current 75% PURE / 25% MARKET architecture;
- log-odds blends, which combine evidence in logit space rather than averaging probabilities;
- walk-forward selected market weights using only earlier OOS seasons;
- disagreement-conditioned regression inspired by nfelo, to be researched separately before any production proposal;
- market-movement-aware regression, which requires timestamp-aligned opening and T−120 market snapshots before it can be fairly validated for Sunday Signal.
