# LevLine 4 literature review: market-first football information residuals

Status: **research-only scientific review; no production authorization**  
As-of: **2026-09-15 America/Los_Angeles**

## Research question

The relevant question is not whether injuries, quarterbacks, lineups, scheme or matchup information matters to football. The relevant question is whether a reproducible point-in-time representation of those states contains **incremental predictive information after conditioning on the same-horizon betting market and the incumbent LevLine forecast**.

The literature strongly supports treating the betting market as a difficult forecast benchmark. It also supports dynamic latent state, player-value estimation, calibration, forecast combination and market-path research as legitimate methodologies. It does **not** establish that a qualitative analyst, an injury list, or a richer feature set should automatically override the market.

## Evidence matrix

| Citation | DOI / link | Sport / sample | Features / model | Validation / benchmark | Reported finding | Limitations | LevLine relevance |
|---|---|---|---|---|---|---|---|
| Boulier & Stekler (2003), *International Journal of Forecasting*, “Predicting the outcomes of National Football League games” | https://doi.org/10.1016/S0169-2070(01)00144-3 | NFL, 1994-2000 | NYT power scores; probit winner forecasts; editor forecasts | Compared with naive forecast and betting market | Betting market was the best predictor; power-score model next | Older market era; winner accuracy rather than modern probabilistic PIT evaluation | Direct warning that football models must prove value beyond market, not merely predict winners well |
| Song, Boulier & Stekler (2007), *International Journal of Forecasting* 23(3):405-413 | https://doi.org/10.1016/j.ijforecast.2007.05.003 | NFL, 496 regular-season games in 2000-2001; 31 statistical systems, 70 experts, nearly 18k expert and 12k model forecasts | Judgmental experts vs statistical models vs betting line | Comparative forecast-accuracy evaluation | Expert/model winner accuracy differences were not significant; betting line outperformed both | Old sample; betting line is not a direct modern moneyline probability; no PIT lineup residual | Strongest NFL-specific warning against subjective/LLM overrides; market is mandatory benchmark |
| Song, Boulier & Stekler (2009), *International Journal of Forecasting* 25(1):182-191 | https://doi.org/10.1016/j.ijforecast.2008.11.006 | NFL, same 2000-2001 expert/model universe | Binary forecast consensus measured with Cohen’s kappa | Winner and against-spread forecast agreement | Substantial agreement, especially among systems; earlier work’s market superiority reiterated | Consensus is not accuracy; old sample | Supports measuring redundancy/consensus before rewarding multiple football signals |
| Boulier, Stekler & Amundson (2006), *Applied Economics* 38(3):279-284 | https://doi.org/10.1080/00036840500368904 | NFL, 1994-2000 | Three market-efficiency tests using publicly knowable information | Betting-line efficiency tests | Did not establish a simple exploitable public-information inefficiency | Spread-betting framing; older era | Public football facts can matter while still being priced; residual edge must be demonstrated |
| Glickman & Stern (1998), *Journal of the American Statistical Association* 93(441):25-35 | https://doi.org/10.1080/01621459.1998.10474084 | NFL, 1988-1993 | Bayesian state-space model; AR(1) evolving team strength, home advantage, week/season evolution | Predictive model with sensitivity/model checks | Demonstrates coherent dynamic latent-strength estimation with shrinkage | Predates modern market/PBP data; not a market-conditioned residual study | Methodological basis for H7, but does not rescue LevLine’s rejected generic Elo/latent candidates |
| Miller & Rapach (2013), *Journal of Empirical Finance* 24:10-23 | https://doi.org/10.1016/j.jempfin.2013.07.002 | NFL; unique weekly sequence of three NYC bookie lines | Early, Tuesday opener, and game-time line; forecast-encompassing tests | Sequential line information content | Later lines encompass more information; evidence of intra-week information incorporation and some sentiment effects | Illegal NYC bookie market; line/spread rather than modern multi-book moneyline | Direct support for H4/H6: information path and event timing are worth measuring, but late state remains hard benchmark |
| Krieger & Davis (2024), *Journal of Economics and Finance* 48:263-279 | https://doi.org/10.1007/s12197-023-09656-5 | NFL, 3,756 regular/postseason games, 2007-2021 | Visibility proxies: TV audience, concurrent games, fanbase; betting-line movement | Regression tests of movement frequency/magnitude | Lower-visibility games experienced more frequent/larger line movement | Studies movement, not probability calibration or a tradable residual rule | NFL-specific support for market microstructure/path research and cross-book breadth/dispersion diagnostics |
| Durand, Patterson & Shank (2021), *Journal of Behavioral and Experimental Finance* 31:100522 | https://doi.org/10.1016/j.jbef.2021.100522 | NFL, 2003-2017 | Prior outcomes/margins; first-string QB participation; betting behavior | Market-behavior regressions | Bettors wagered 2.1% less on home team when home QB1 did not play and 3.1% more when visitor QB1 did not play; interpreted as overreaction evidence | Betting behavior is not directly calibrated win probability; QB participation chronology may differ from LevLine’s horizon | Strong H2/H6 motivation and equally strong double-counting warning: QB news demonstrably moves markets |
| Gray & Gray (1997), *Journal of Finance* 52:1725-1737 | https://doi.org/10.1111/j.1540-6261.1997.tb01129.x | NFL betting market | Probit models / betting-line efficiency variables | Out-of-sample betting tests | Some predictable structure reported, with instability and practical limits | Old era, spread-return objective, multiple-strategy risk | Historical evidence that apparent edge must survive strict OOS/stability and transaction/friction logic |
| Golec & Tamarkin (1991), *Journal of Financial Economics* 30:311-323 | https://doi.org/10.1016/0304-405X(91)90034-H | NFL and college football, long historical sample | Betting-market bias tests | Cross-season betting efficiency | Reported selected biases, while persistence/transaction economics matter | Very old market; betting return rather than probability quality | Reinforces season-stability and predeclared-rule requirements |
| Vandenbruaene, De Ceuster & Annaert (2022), *Journal of Sports Economics* 23(7):907-949 | https://doi.org/10.1177/15270025211071042 | Sports-betting literature review, >600 point-spread strategy implementations | Review of betting-market anomalies and strategy testing | Meta-level assessment of market efficiency evidence | Predictable glitches can coexist with broad efficiency and often fail to imply economically meaningful exploitation | Review spans heterogeneous eras/sports/methods | Strong anti-feature-mining prior: tiny subgroup gains are not enough for LevLine promotion |
| Štrumbelj (2014), *International Journal of Forecasting* 30(4):934-943 | https://doi.org/10.1016/j.ijforecast.2014.02.008 | 37 competitions across five sports; 412 bookmaker/competition pairs | Multiple implied-probability / margin-removal methods; bookmaker identity | Forecast accuracy of odds-derived probabilities | De-vig method and bookmaker identity can affect probability accuracy; Shin often performed well in studied markets | Mostly multi-outcome/non-NFL markets; two-way NFL moneylines have different algebraic structure | Supports H5 ablations, not importing a favored de-vig or “sharp book” assumption |
| Angelini & De Angelis (2019), *International Journal of Forecasting* 35(2):712-721 | https://doi.org/10.1016/j.ijforecast.2018.07.008 | Association football; 41 bookmakers, 11 European leagues, 11 years | Forecast-based tests of bookmaker-market efficiency | Cross-book / cross-league forecast evaluation | Found differing degrees of forecast efficiency among bookmakers and markets | Soccer three-way odds; no NFL PIT transfer guarantee | Supports testing fixed historical book quality only when LevLine has equivalent PIT NFL history; folklore weights prohibited |
| Hegarty & Whelan (2025), *International Journal of Forecasting* 41(2):803-820 | https://doi.org/10.1016/j.ijforecast.2024.06.013 | Association football | Traditional and Asian-handicap market probabilities / mappings | Market forecast comparison | Demonstrates that market representation/construction can materially affect forecast quality | Soccer-specific market structure | Supports treating market construction as a candidate feature-engineering problem rather than one immutable upstream number |
| Dare, Dennis & Paul (2015), *Finance Research Letters* 13:130-136 | https://doi.org/10.1016/j.frl.2015.02.004 | NBA, large multi-season sample with player absences | Player absence, player importance, opening vs closing betting line | Opening and closing line efficiency | Opening lines had meaningful errors around absences; biases were removed by the close and no closing-line profitable strategy remained | NBA substitution/roster structure differs greatly from NFL; spread not moneyline probability | Crucial transfer warning for H1/H6: lineup info may add early and disappear after market digestion; horizon matters |
| Yurko, Ventura & Horowitz (2019), *Journal of Quantitative Analysis in Sports* 15(3):163-183 | https://doi.org/10.1515/jqas-2018-0010 | NFL offensive players; public play-by-play | nflWAR; expected-points / win-probability-based player valuation; reproducible public pipeline | Player-evaluation validation / interpretability | Provides reproducible outcome-linked player-value framework | Retrospective player value is not pregame availability and not proof of market residual value | Supports H1’s player-value substrate and replacement concept, with strict lagging/PIT firewall required |
| Sabin (2021), *Journal of Quantitative Analysis in Sports* | https://doi.org/10.1515/jqas-2020-0033 | NFL player evaluation | Regularized adjusted plus-minus style player contribution estimation | Player-value modeling | Demonstrates shrinkage-based estimation of individual contribution in a highly interdependent sport | On-field contribution estimation, not PIT pregame forecast increment; attribution remains difficult | Supports conservative shrinkage/replacement-level concepts, not direct probability points |
| Baio & Blangiardo (2010), *Journal of Applied Statistics* 37(2):253-264 | https://doi.org/10.1080/02664760802684177 | Association football | Bayesian hierarchical score model | Predictive checks / hierarchical pooling | Demonstrates hierarchical partial pooling and also potential overshrinkage issues | Soccer scoring process differs materially from NFL; not market-conditioned | Methodological support for H3 shrinkage; no direct transfer of football effect sizes |
| Ghilagaber & Munezero (2020), *Journal of Applied Statistics* 47(2):248-264 | https://doi.org/10.1080/02664763.2019.1635572 | Association football | Bayesian change-point model around structural/rule change | Before/after regime modeling | Demonstrates a principled framework for structural-break inference | League/rule change, not NFL team-specific regime forecasting | Methodological support for H7 only after PIT regime labels are frozen |
| Gneiting & Raftery (2007), *JASA* 102(477):359-378 | https://doi.org/10.1198/016214506000001437 | General probabilistic forecasting | Strictly proper scoring rules including quadratic/Brier and logarithmic score | Theoretical | Proper scores incentivize truthful probability forecasts | Not sports-specific | Justifies LevLine’s Brier/log-loss safeguards and rejection of accuracy-only promotion |
| Gneiting, Balabdaoui & Raftery (2007), *JRSS B* 69(2):243-268 | https://doi.org/10.1111/j.1467-9868.2007.00587.x | General probabilistic forecasting | Calibration, sharpness, proper scoring diagnostics | Theoretical + empirical illustration | Forecasts should maximize sharpness subject to calibration | Not sports-specific | Supports reporting calibration intercept/slope, reliability and sharpness rather than accuracy alone |
| Ranjan & Gneiting (2010), *JRSS B* 72(1):71-91 | https://doi.org/10.1111/j.1467-9868.2009.00726.x | General probability forecasts | Linear pools and beta-transformed pools | Theoretical + empirical forecast combination | Non-trivial linear pooling of calibrated probabilities can become uncalibrated; proposes recalibrated pool | Not sports-specific | Direct caution for market/PURE ensembles; combination requires calibration audit |
| Kull, Silva Filho & Flach (2017), AISTATS / PMLR 54:623-631 | https://proceedings.mlr.press/v54/kull17a.html | Binary classifiers, multiple datasets | Beta calibration vs logistic/isotonic | Held-out calibration experiments | Beta calibration includes identity and can avoid logistic miscalibration; isotonic can overfit small samples | ML benchmark datasets, not NFL | Supports identity as baseline and beta as explicit candidate only with independent chronological calibration data |
| Timmermann (2006), *Handbook of Economic Forecasting* | https://doi.org/10.1016/S1574-0706(05)01004-9 | General forecasting | Forecast combinations, estimated vs simple weights | Review/theory | Estimation error can make sophisticated “optimal” weights worse than simple/shrunk combinations | Not sports-specific | Supports aggressive regularization and smallest-winning-architecture principle |
| Wang, Hyndman, Li & Kang (2023), *International Journal of Forecasting* 39(4):1518-1547 | https://doi.org/10.1016/j.ijforecast.2022.11.005 | General forecasting, 50+ year review | Point/probabilistic forecast combinations, time-varying/nonlinear weights | Review | Combination often helps, but method choice, estimation error and calibration remain central | Not sports-specific | Supports constrained ensemble testing, not a large unconstrained model tournament |
| Grant & Johnstone (2010), *International Journal of Forecasting* 26(3):498-510 | https://doi.org/10.1016/j.ijforecast.2010.01.002 | Australian Football League probability forecasts | Pooling forecasters selected with proper scoring/profit criteria | Paper betting against market odds | Shows that combining probability forecasters can improve decision performance in some settings | Different sport/market; panel forecasts unlike LevLine features; betting-profit objective | Positive evidence that independent forecast information can combine with market, but independence must be demonstrated |

## Current non-peer-reviewed evidence worth tracking, not using as authority

### Vlachmpeis (2026), “The Incremental Value of Player Information in Football Match Prediction”

- Link: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7295578
- Status: SSRN working paper posted August 2026; **not peer reviewed at the time of this review**.
- Sport/sample: top-division European association football; 7,801 eligible matches across Belgium, Netherlands, Portugal, Scotland and Turkey. Development sample 6,638 matches from 2020/21-2024/25; final held-out test 1,163 matches from 2025/26.
- Question: whether recent performance information about identified starters improves three-way predictions beyond a recalibrated closing bookmaker market.
- Relevance: unusually close to LevLine H1’s *incremental-to-market* framing. It is useful as a contemporaneous caution if its held-out player layer fails to add stable value, but it cannot substitute for peer-reviewed NFL evidence or LevLine’s own PIT tests.

## What transfers to the NFL, and what does not

### High-confidence transfer

The following are domain-general statistical principles and should govern LevLine directly:

- proper scores for probability selection;
- calibration and sharpness reporting;
- chronological/out-of-sample validation;
- conservative forecast combination and shrinkage;
- dependence-aware paired uncertainty;
- explicit provenance and no-lookahead data contracts.

### Moderate transfer

The following are plausible methodologies but require NFL-specific validation:

- Bayesian/hierarchical player and unit partial pooling;
- change-point/state-space representations of structural breaks;
- bookmaker-specific consensus weighting;
- calibration transforms;
- market-path microstructure features.

### Low transfer / hypothesis generation only

The following cannot supply NFL effect sizes or production weights:

- soccer lineup interaction effects;
- NBA player-absence line effects;
- soccer bookmaker rankings;
- soccer score-model coefficients;
- qualitative beat-report assessments.

The NFL has unusually small seasonal samples, discrete weekly information releases, severe position asymmetry (especially QB), high substitution specialization, correlated injuries by unit, and a betting market that often reacts quickly to public injury news. Those differences make direct coefficient transfer scientifically indefensible.

## Literature-derived implications for H1-H10

**H1 expected lineup residual.** Player value is measurable, but market-efficiency and NBA absence evidence imply the key unknown is not whether missing players matter; it is whether their impact remains unpriced at the chosen horizon. Test lineup *shock* conditional on same-horizon market, not injury count or absolute talent alone.

**H2 QB scenario/replacement.** NFL market behavior already changes around QB1 absence. QB therefore deserves a separate state and explicit replacement model, but this increases—not decreases—the need to control for the contemporaneous market to avoid double counting.

**H3 personnel-conditioned matchups.** Hierarchical shrinkage is methodologically defensible. Generic interactions have weak priors after LevLine’s own failures; only a tiny fixed set of football-mechanism interactions should be tested after expected personnel state is credible.

**H4 market path.** NFL sequential-line and visibility research directly supports preserving how a price evolved. It does not justify a predetermined “follow steam” or “fade reversal” rule. Path variables must compete conditionally on the final same-horizon probability.

**H5 bookmaker quality/consensus.** Cross-book quality differences are empirically plausible, but the strongest evidence is mostly soccer. LevLine should prefer robust unweighted consensus until NFL PIT history can support frozen book weights without 2026 outcome selection.

**H6 inactive information surprise.** Cross-sport player-absence evidence suggests that information can be mispriced at open and efficiently absorbed by close. The correct first experiment is an event study separating football-state surprise from market response, followed by a separately preregistered residual model only if unexplained structure remains.

**H7 structural regime change.** State-space/change-point methods are coherent, but LevLine’s generic dynamic-strength failures lower the prior. Only explicitly labeled structural events justify a new candidate identity.

**H8 structured beat intelligence.** The literature gives no scientific basis for free-text sentiment or analyst picks as direct probability features. Beat reporting is potentially valuable as a timestamped measurement channel for expected starter/role/scheme states. Extraction quality and forecast effect must be evaluated separately.

**H9 uncertainty-aware shrinkage.** Forecast-combination/calibration theory supports shrinking unreliable corrections. Uncertainty cannot manufacture direction; it can only moderate an independently validated directional residual.

**H10 conditional scenario engine.** Scenario mixing is coherent only when starter probabilities and conditional win models are themselves validated. Until then, conditional numbers would be narrative estimates disguised as model output.

## Scientific conclusion from the literature alone

The literature does **not** justify a large football-first LevLine 4. It supports a **market-first, information-timing architecture** in which proprietary football state earns only a small residual role after same-horizon conditioning. The highest-value unresolved empirical questions are therefore:

1. whether expected-lineup/QB state remains informative after the post-inactive market has moved;
2. whether the path and cross-book structure of that move contains information beyond the current price;
3. whether robust source/uncertainty measurement improves residual shrinkage and conditional scenario capability.

If none of those survive paired OOS/prospective testing, retaining the market/F-ST backbone is the scientifically correct result.
