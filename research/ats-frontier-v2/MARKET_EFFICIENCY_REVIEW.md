# MARKET EFFICIENCY REVIEW

## Bottom line

The strongest defensible prior is that modern NFL markets are difficult to beat systematically, especially near close. The literature contains anomalies, but they are heterogeneous across samples, eras and specifications. Phase 1 therefore treats the contemporaneous market as the primary forecasting null, not as just another feature.

## Evidence synthesis

- Classic NFL studies report mixed statistical inefficiencies, but several broad tests fail to establish economically reliable exploitation after commission or under alternative specification.
- Miller & Rapach's sequential-line analysis is particularly important mechanistically: the opening line contains information beyond an earlier outlaw line and the closing line contains information beyond opening. That pattern is price discovery.
- Player-absence work in the NBA shows a relevant timing pattern: opening lines can be biased around meaningful absences, but the bias is largely eliminated by close. This is exactly why M2 is framed as an event-timed information delta instead of a static injury feature.
- Shank's information-asymmetry work suggests book response, betting percentages and line direction can contain information, but those effects require strong replication because they use proprietary Sports Insights data and can be regime-dependent.
- A 2026 NFL thesis spanning 6,185 games finds closing absolute error roughly stable through the season, with localized rather than broad early-season inefficiency. This pushes against generic “uncertainty early in year” strategies.
- A 2026 Finance Research Letters key-number discontinuity study finds economically meaningful betting-demand jumps at 3 and 7 without corresponding return discontinuities. Market microstructure can be real without offering predictive return alpha.

## Implications for Frontier V2

1. **Do not target unconditional game prediction.** A candidate must beat a market null on the same timestamp and rows.
2. **Earlier is not automatically easier.** An early model may look more independent but will be compared with the market state actually available at that horizon.
3. **Closing line is informative but not necessarily the operational target.** If a candidate is intended for T-120, compare it against T-120 market state and separately evaluate subsequent CLV.
4. **Anomaly mining is prohibited.** Historical favorite/underdog, streak, playoff-position and weather anomalies are literature context, not candidate features unless a causal/information mechanism survives preregistration.
5. **Statistical significance is insufficient.** Commission, push probability, available side price, multiple testing and nonstationarity matter.

## Research prior

The planning prior for a durable market-relative effect should be small. A sustained 58–60% ATS record is treated as a leakage/selection warning until supported by extensive independent or prospective evidence. Proper-score improvement and calibration are the primary scientific outcomes; raw ATS is secondary.