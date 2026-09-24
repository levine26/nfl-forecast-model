# SOURCE LEDGER

Evidence classes: **1** peer-reviewed; **2** strong technical preprint/working paper; **3** reproducible open source; **4** disclosed practitioner work; **5** opaque commercial/public system; **6** speculative/social-media claim. Phase 1 gives substantially more weight to classes 1–3.

## Academic / technical sources

| # | Source | Class | Method / sample | Frontier relevance and limitation |
|---|---|---:|---|---|
| A01 | Golec & Tamarkin (1991), *The degree of inefficiency in the football betting market*, JFE 30, DOI `10.1016/0304-405X(91)90034-H` | 1 | NFL betting-market tests | Found some biases but economic exploitability depends on transaction costs; foundational warning that statistical inefficiency != edge. |
| A02 | Dare & MacDonald / related 1990s NFL efficiency literature summarized in later reviews | 1 | spread efficiency / specification | Relevance: model specification materially changes anomaly conclusions. Use as background, not a direct modern edge claim. |
| A03 | Gray & Gray (1997), *Testing market efficiency: evidence from the NFL sports betting market* | 1 | probit / NFL spreads | Historical evidence of conditional patterns; age/regime dependence is a limitation. |
| A04 | Kochman & Goodwin (2004), *An underdog anomaly in the NFL betting market*, J Sports Econ, DOI `10.1177/1527002504264426` | 1 | NFL favorites/underdogs | Historical anomaly; must test stability and post-publication decay before any modern use. |
| A05 | Boulier, Stekler & Amundson (2006), *Testing the efficiency of the NFL betting market*, Applied Economics, DOI `10.1080/00036840500368904` | 1 | 1994–2000 NFL | No conclusive broad inefficiency; supports strong market null. |
| A06 | Miller & Rapach (2013), *An intra-week efficiency analysis of bookie-quoted NFL betting lines in NYC*, J Empirical Finance 24 | 1 | outlaw/open/close lines; 1972 NFL | Information content rises through the week; supports dynamic information-state framing. Historical/illegal-market sample limits direct parameter transfer. |
| A07 | Shank (2018), *Is the NFL Betting Market Still Inefficient?*, J Economics & Finance 42 | 1 | modern-ish NFL spreads/totals | Reports conditional inefficiencies; useful hypothesis evidence, not a transferable rule without prospective replication. |
| A08 | Shank (2022), *Information asymmetry in the NFL gambling market*, J Behavioral & Experimental Finance 36, DOI `10.1016/j.jbef.2022.100758` | 1 | 2003–2017 Sports Insights line/bet-money data | Suggests bettor/book interaction contains information; motivates M1 money/bet-flow research where legally/data-feasible. |
| A09 | Tuttle, Pion & Bumpass (2024), *An Examination of the Money Line Market for NFL Games*, Journal of Economic Insight 50(2) | 1 | 2007–2016 open/close moneylines | Inefficiencies vary by season; motivates spread–moneyline cross-market state but warns instability. |
| A10 | White (2026), *Information, Uncertainty, and Betting Market Accuracy Across the NFL Season*, CMC thesis | 2 | 6,185 games, 2002–2025 | Closing absolute error roughly stable through season; supports broadly efficient market and skepticism of generic early-season edge. Not peer-reviewed. |
| A11 | *Do economically meaningful quote differences convey private information?* (2026), Finance Research Letters, DOI `10.1016/j.frl.2026.110193` | 1 | NFL key-number regression discontinuity | 3/7 cause demand discontinuities but no return discontinuity; key numbers matter structurally, not automatically as alpha. |
| A12 | Dare, Dennis & Paul (2015), *Player absence and betting lines in the NBA*, Finance Research Letters 13, DOI `10.1016/j.frl.2015.02.004` | 1 | player absences; opening vs closing | Opening biases tied to absences largely disappear by close. Transfer: timing/uncertainty can matter; static known absence likely priced. |
| A13 | Gandar et al. (1998), *Informed Traders and Price Variations in the Betting Market for Professional Basketball Games*, Journal of Finance, DOI `10.1111/0022-1082.155346` | 1 | open→close line changes | Line changes improve forecasts and remove opening bias; cross-domain support for price discovery / M1. |
| A14 | Hoffer & Pincin (2019), *Quantifying NFL Players’ Value With the Help of Vegas Point Spread Values*, J Sports Econ, DOI `10.1177/1527002519832060` | 1 | sportsbook player point-spread values | QBs dominate player spread value; supports separate QB state and replacement gap. Proprietary PSV construction limits reproduction. |
| A15 | Yurko, Ventura & Horowitz (2019), *nflWAR*, JQAS 15(3), DOI `10.1515/jqas-2018-0010` | 1 | PBP EP/WP + multilevel player effects | Reproducible player ability/value with uncertainty; supports hierarchical player-value component. Ex-post player value is not itself PIT availability. |
| A16 | Glickman & Stern (1998), *A State-Space Model for NFL Scores*, JASA 93 | 1 | 1988–1993 NFL; dynamic team strengths | Direct precedent for week-to-week and season-to-season latent strength evolution. Does not prove incremental value over modern markets. |
| A17 | Dixon & Coles (1997), *Modelling Association Football Scores and Inefficiencies in the Football Betting Market*, JRSS-C 46, DOI `10.1111/1467-9876.00065` | 1 | dynamic Poisson soccer score model | Dynamic strengths + score distribution; transfers architecture concepts, not scoring distribution parameters. |
| A18 | Crowder, Dixon, Ledford & Robinson (2002), dynamic football attack/defence state-space model, Statistician, DOI `10.1111/1467-9884.00308` | 1 | time-varying soccer strength | Supports latent offense/defense states and temporal smoothing; soccer-to-NFL transfer risk. |
| A19 | Karlis & Ntzoufras (2003), *Analysis of sports data by using bivariate Poisson models*, Statistician 52, DOI `10.1111/1467-9884.00366` | 1 | joint scores with dependence | Supports modeling joint score dependence rather than independent outcomes; NFL scoring lattice differs materially. |
| A20 | Koopman & Lit (2015-era work), dynamic bivariate count/state-space sports forecasting | 1 | non-Gaussian state space | Supports computationally efficient dynamic latent strengths; transfer requires NFL-specific distribution. |
| A21 | Ridall & Pettitt (2024/2025), Bayesian state-space football team performance, JRSS-C, DOI `10.1093/jrsssc/qlae075` | 1 | Bayesian dynamic attack/defense | Modern hierarchical state-space evidence; useful for M3 uncertainty/process-noise design. |
| A22 | Ingram (2019), Gaussian-process dynamic paired-comparison models | 2 | time-varying paired comparisons | Shows flexible temporal strength evolution can beat fixed rating updates in other sports; computational/sample-size caution. |
| A23 | Dmochowski (2023), *A statistical theory of optimal decision-making in sports betting*, PLOS ONE 18, DOI `10.1371/journal.pone.0287601` | 1 | >5,000 NFL games; conditional quantiles / betting decisions | Median predicts side; additional quantiles matter for wager selectivity. Supports distributional decision framing, not a claim that LevLine can beat market. |
| A24 | Gneiting & Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*, JASA 102, DOI `10.1198/016214506000001437` | 1 | scoring-rule theory | Proper scores must govern probabilistic candidate selection; ATS hit rate is secondary/noisy. |
| A25 | Gneiting & Ranjan (2010), *Combining Probability Forecasts*, JRSS-B 72 | 1 | linear/beta-transformed pools | Distinct calibrated forecasts can become uncalibrated when naively pooled; supports recalibrated combination only after complementarity. |
| A26 | Claeskens, Magnus, Vasnev & Wang (2016), *The forecast combination puzzle*, IJF 32, DOI `10.1016/j.ijforecast.2015.12.005` | 1 | estimated combination weights | Estimated “optimal” weights add estimation error; direct warning against another small-sample stacking rescue. |
| A27 | Rigby & Stasinopoulos (2005), *GAMLSS*, JRSS-C 54, DOI `10.1111/j.1467-9876.2005.00510.x` | 1 | location/scale/shape regression | Candidate tool for conditional heteroskedastic/skew/tail structure; implementation option, not mechanism. |
| A28 | Duan et al. (2020), *NGBoost*, ICML/PMLR 119 | 1 | natural-gradient probabilistic boosting | Flexible full-distribution learner; useful only if sample-efficient in frozen design. |
| A29 | Schlosser et al. (2018), distributional regression forests for probabilistic forecasting, arXiv `1804.02921` | 2 | weather distributional post-processing | Cross-domain evidence that forests can model all distribution parameters; NFL sample-size risk. |
| A30 | Gneiting et al. probabilistic forecast calibration/sharpness literature | 1 | weather/probability forecasts | Reliability + sharpness framework transfers directly to cover/push/loss and margin PMFs. |
| A31 | Dynamic Bradley–Terry / Elo/Glicko literature summarized in modern sports-rating reviews | 1 | paired comparisons | Supports partial pooling and evolving strengths; exact update equations are not presumed optimal for NFL ATS. |
| A32 | Recent Bayesian dynamic paired-comparison work with innovation/changepoint shrinkage (2026 technical literature) | 2 | sudden-strength changes | Mechanistic support for regime-aware M3; must be independently replicated before parameter adoption. |

## Reproducible/open-source systems inspected or surveyed

| ID | Repository/package | Class | What was inspected / transferable concept |
|---|---|---:|---|
| O01 | `greerreNFL/nfelo` | 3 | Active Python model; market-regression modules, opening/closing regression, CLV utilities, training benchmarks. Explicitly trades model independence against market accuracy. |
| O02 | `greerreNFL/nfelotranslation` | 3 | Separate Distribution/Key/Normalizer/SpreadMap/Translation modules; margin→spread/cover/push/EV translation; directly relevant to M4 numerical design. |
| O03 | `ShamgarBN/nfl-bet-engine` | 3 | Real source tree includes backtest/ablation/tuning/walkforward, model/features/predict; disclosed LightGBM + Monte Carlo + calibration. Useful engineering patterns; claims not imported as evidence of edge. |
| O04 | `dmochow/optimal_betting_theory` | 3 | Paper-linked repository with code/data/docs; reproducible decision-theory companion to A23. |
| O05 | `nflverse/nflreadr` | 3 | Canonical access layer for PBP, rosters, injuries, depth charts, snap counts, NGS and related releases. |
| O06 | `nflverse/nflverse-data` | 3 | Release-based data store and update cadence; crucial provenance source. |
| O07 | `nflverse/nflverse-rosters` | 3 | Workflows for rosters/depth charts/practice reports; source changed after 2024. |
| O08 | `nflverse/nflfastR` | 3 | PBP infrastructure and derived EPA/WP ecosystem; appropriate ex-post ability training source when chronology-safe. |
| O09 | `nfl-data-py` | 3 | Python interface to nflverse-style data; convenience layer only, not independent provenance. |
| O10 | `stanfordmlgroup/ngboost` | 3 | Reference implementation of A28; possible Phase-3 tool after preregistration. |
| O11 | `gamlss-dev/gamlss` / R GAMLSS ecosystem | 3 | mature multi-parameter distributional regression implementation. |
| O12 | `partykit` / distributional forest ecosystem | 3 | tree-based conditional distribution parameter estimation; possible small-sample alternative. |
| O13 | nflverse `nfl4th` | 3 | fourth-down value/decision infrastructure; useful for team aggressiveness features only if PIT-safe and mechanism survives later review. |
| O14 | public FiveThirtyEight-style NFL Elo implementations surveyed | 3/4 | rating + QB adjustment patterns; mostly historical/derivative, useful as architecture context rather than modern edge evidence. |
| O15 | public NFL Elo/prediction repositories surfaced in GitHub search | 3/6 | broad survey found many shallow/legacy projects; none justified replacing the mechanism-first shortlist. |

## Practitioner/professional systems reviewed

| ID | System | Class | Finding |
|---|---|---:|---|
| P01 | nfelo | 3/4 | Most useful public engineering comparator: explicit market regression, QB adjustments, CLV and margin translation. |
| P02 | Dimers | 4 | Discloses >100 inputs and separate margin/total ML systems with QB, efficiency, pace, rest/travel/weather; proprietary fitted method. |
| P03 | Fourth & Value | 4 | Strong public transparency around multi-book odds, fair-probability normalization, player/injury context and family-specific models; current public emphasis includes props. |
| P04 | ESPN FPI | 4/5 | Public descriptions emphasize EPA/play, opponent/trash-time adjustment, QB injury factor, backup value, starter changes and market-informed preseason priors in some versions. Fitted system proprietary. |
| P05 | PFF power rankings / spread ratings | 5 | Public team/QB point-spread ratings and simulations; insufficient reproducible methodology for parameter transfer. |
| P06 | Football Outsiders / FTN DVOA lineage | 4/5 | Situation- and opponent-adjusted play efficiency, including special teams; useful conceptual benchmark, proprietary weights. |
| P07 | historical FiveThirtyEight NFL Elo | 4 | Transparent rating/QB adjustment lineage; useful benchmark architecture but discontinued as a live official system. |
| P08 | Sagarin ratings | 5 | Long-running public ratings; methodology not sufficiently disclosed for reproduction in this program. |
| P09 | Massey-style rating systems | 4/5 | Comparative/rating-system context; not evidence of ATS incrementality. |
| P10 | David Sasser public work | 4/5 | Current public site exposes college-football projected scores/lines and market comparison; no reproducible current NFL betting methodology located. Do not infer hidden NFL method. |
| P11 | public 2026 ELWAY / margin-translation practitioner analyses | 4 | Useful empirical key-number/tail checks; lower evidence weight than peer-reviewed/fully reproducible work. |

## Data/provider sources reviewed

Provider details are normalized in `MARKET_DATA_SOURCE_MATRIX.md` and `NFL_DATA_SOURCE_MATRIX.md`. Sources include The Odds API, PropLine, SportsDataIO, Sportradar, Sports Insights/Bet Labs, Pinnacle API, Circa public markets, Action Network public market screens, nflverse, PFR/NGS-derived nflverse datasets, FTN/DVOA concepts, and public weather/stadium sources.

## Saturation conclusion

The research did not identify a credible basis for another generic football-feature learner. Independent literatures instead converge on four scientific opportunities: richer dynamic market state, timestamped player/QB information changes, latent temporal strength with uncertainty/regimes, and better full-distribution representation. The first two are information-channel hypotheses; the latter two are state/representation hypotheses whose incremental value is much less certain.