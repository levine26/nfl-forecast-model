# External market-regression references

Sunday Signal's market audit is informed by public NFL forecasting approaches beyond the SuJaR baseline. In particular, nfelo treats market regression as a dynamic accuracy-versus-alpha problem rather than a fixed assumption: small model/market disagreements can be collapsed toward market, extreme opinions can be capped, and open-to-close movement can alter the amount of regression. Sunday Signal will measure these ideas on held-out or prospective timestamp-aligned data, but will not mutate frozen `F-ST-01-FROZEN-2026` from 2026 outcomes or closing-line optimization.

Production version `0.9.0-fst` uses the frozen F-ST market + nested-PURE logit stack. The former 75% legacy PURE / 25% MARKET architecture is retained exactly as `legacy_final_home_prob` for prospective counterfactual evaluation; it is no longer the official production winner probability when a usable market probability exists.

Candidate/reference families used by the audit include:

- frozen `F-ST-01-FROZEN-2026`, the official market + nested-PURE logit stack;
- the legacy fixed 75% PURE / 25% MARKET counterfactual;
- market-only probability on the same snapshot;
- F-ST nested PURE where useful as a football-only reference;
- separately registered future disagreement-conditioned or market-movement-aware candidates, which require chronology-safe timestamped evidence before any production proposal.
