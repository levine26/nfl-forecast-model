# QB VALUE RESEARCH

QB state is sufficiently important and uncertain to be separated from generic personnel modeling.

## Evidence

- ESPN's public FPI development discussion identifies the QB injury factor as one of the hardest/most distinctive NFL modeling components and describes age/efficiency-based QB impact plus backup strength.
- Hoffer & Pincin's sportsbook point-spread-value study finds quarterback values dominate other positions.
- Public QB evaluation research supports EPA/play and CPOE-style measures as more informative than raw completion/box-score metrics, but retrospective efficiency must be shrunk and opponent/context adjusted.
- Adaptive Candidate 2's only favorable 2025 switch occurred around a QB1 identity-change event. That is not validation, but it supports the scientific importance of prospectively modeling such events rather than ignoring them.

## Required latent QB state

A future preregistration should consider a hierarchical state containing:

- prior multi-season ability with age/experience shrinkage;
- recent EPA/play + CPOE-style signal with opponent and game-state adjustment;
- pressure/sack/decision components only if stable and PIT-feasible;
- rookie prior / college or draft information handled separately and conservatively;
- injury/participation probability;
- starter probability where coach decision is uncertain;
- backup/replacement ability distribution;
- parameter uncertainty, especially for small-sample backups/rookies.

Expected QB value at horizon `t` must integrate over possible starters rather than inserting the eventually realized starter when that was not known:

`E[QB_value_t] = Σ_j P(starter=j | info_t) × value_j,t`.

## Market conditioning

The causal football importance of QB is not the betting hypothesis. The hypothesis is that a well-timestamped QB state may occasionally update before or differently from the market. Therefore Phase 4, if reached, must compare any QB information delta against the same-horizon spread + price + market path.

## Failure risks

- Market makers and informed bettors may estimate QB point value better than public models.
- Public injury/starter probabilities may update too slowly or be inaccessible historically.
- EPA/CPOE histories are noisy and scheme/support dependent.
- Backup samples are extremely small; unpooled estimates will overfit.
- Any use of confirmed final starter/inactives before their real publication time is leakage.

## Phase-1 conclusion

QB modeling is **not a separate fifth candidate**. It is a mandatory high-value submodel inside `FRONTIER-M2-PLAYER-STATE-DELTA` and a state component potentially shared with M3.