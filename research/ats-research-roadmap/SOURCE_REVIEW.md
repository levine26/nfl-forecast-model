# LevLine ATS Research — Literature and Open-Source Review

**Review date:** 2026-09-25  
**Purpose:** identify mechanisms that are genuinely incremental to the completed LevLine ATS research rather than collect more model architectures  
**Completed-2026 LevLine outcomes used:** none

## Review method

The source review was organized around five questions:

1. How efficiently do betting markets aggregate information through time?
2. Can different market instruments contain nonredundant information?
3. What should count as a scientifically valid probabilistic improvement?
4. Which open/public data can support point-in-time NFL testing without temporal relabeling?
5. Which methods are plausibly useful **after** a real information gain exists, versus methods that merely repackage the same inputs?

The review intentionally distinguishes:

- **external empirical evidence** from other samples/sports;
- **methodological guidance** from forecasting/statistics literature;
- **LevLine-specific evidence** from this repository.

External evidence motivates hypotheses. It does not override LevLine preregistrations, negative results, chronology contracts, or production firewalls.

---

## 1. Sequential betting lines and information aggregation

### Miller & Rapach (2013) — NFL intra-week line efficiency

**Source:** Thomas W. Miller Jr. and David E. Rapach, “An intra-week efficiency analysis of bookie-quoted NFL betting lines in NYC,” *Journal of Empirical Finance* 24 (2013), 10–23. DOI: https://doi.org/10.1016/j.jempfin.2013.07.002

**What the paper contributes:**

The study uses three sequential NFL betting lines within the same betting week rather than only opener/closer observations. Its forecast-encompassing results indicate that information content generally increases as the week progresses. It also reports evidence of sentiment-related pricing inefficiencies and documents profitable activity by professional gamblers in its sample.

**LevLine implication:**

The paper supports treating the market as a **sequential information aggregator** rather than a single static number. It does not establish that a modern public model can beat current NFL markets. For LevLine, its strongest relevance is to M1: a T-120 model should ask whether dispersion, breadth, stale quotes, price-only movement, and prior-path state contain information beyond the contemporaneous T-120 level.

**Important caveat:**

The sample and market structure are historical and specific. It is evidence for the mechanism, not a transferable edge estimate.

---

### Simon (2024) — real-time line movement and weak-form efficiency

**Source:** Jay Simon, “Inefficient Forecasts at the Sportsbook: An Analysis of Real-Time Betting Line Movement,” *Management Science* 70(12), 8583–8611. DOI: https://doi.org/10.1287/mnsc.2022.00456

**What the paper contributes:**

Using detailed opening-to-closing paths from four sportsbooks over 3,681 MLB games, Simon finds that sportsbook forecasts are mostly reliable but not perfectly weak-form efficient. Forecast quality does not improve monotonically in every setting, and line changes exhibit significant negative autocorrelation in the sample.

**LevLine implication:**

This is strong methodological support for studying **the path and microstructure of market forecasts**, not just their final level. It is especially relevant to M1’s separately frozen future-market target because a path signal should first demonstrate that it predicts a later market state after conditioning on the current state.

**Important caveat:**

This is MLB, not NFL. LevLine should transfer the research design idea—not the effect size or a presumed strategy.

---

## 2. Cross-market information: spread versus moneyline

### Fodor, Krieger, Kirch & Kreutzer (2012) — NFL spread/moneyline informational differences

**Source:** Andy Fodor, Kevin Krieger, David Kirch, and Andrew Kreutzer, “Informational Differences in NFL Point Spread and Moneyline Markets,” *Journal of Prediction Markets* 6(2), 1–11. DOI: https://doi.org/10.5750/jpm.v6i2.498 ; working-paper record: https://ssrn.com/abstract=2047243

**What the paper contributes:**

The authors test whether the finer moneyline market contains information not fully expressed by games sharing the same point spread. Their sample reports exploitable differences associated with moneyline information conditional on a common spread.

**LevLine implication:**

This aligns directly with one of the few positive results already preserved in the repository: market-moneyline information improved sign-mass calibration over a spread-only key-mass distribution. It therefore supports the existing rule:

> keep the spread as the location anchor, while allowing moneyline information to refine the sign/win-mass allocation rather than replacing the spread center.

**Important caveat:**

The historical paper does not validate a modern betting rule. LevLine’s own matched OOF evidence is the controlling reason to retain moneyline-informed sign mass.

---

## 3. Probabilistic forecast evaluation

### Gneiting, Balabdaoui & Raftery (2007) — calibration and sharpness

**Source:** Tilmann Gneiting, Fadoua Balabdaoui, and Adrian E. Raftery, “Probabilistic Forecasts, Calibration and Sharpness,” *Journal of the Royal Statistical Society: Series B* 69(2), 243–268. DOI: https://doi.org/10.1111/j.1467-9868.2007.00587.x

**Core principle:**

Good probabilistic forecasting seeks sharp predictive distributions **subject to calibration**. Proper scoring rules and calibration diagnostics evaluate the forecast distribution rather than only its winner classification.

**LevLine implication:**

This supports the program’s existing insistence that CPL log loss/Brier/calibration govern advancement and that ATS hit rate cannot rescue a poorly calibrated probability model. It also explains why a candidate that flips one or two more winners while worsening probability quality is not established progress.

---

### Gneiting & Raftery (2007) — strictly proper scoring rules

**Source:** Tilmann Gneiting and Adrian E. Raftery, “Strictly Proper Scoring Rules, Prediction, and Estimation,” *Journal of the American Statistical Association* 102(477). DOI: https://doi.org/10.1198/016214506000001437

**Core principle:**

Strictly proper scoring rules reward an honest predictive distribution and make the correct probability distribution uniquely optimal in expectation.

**LevLine implication:**

The primary metric for a probabilistic ATS challenger should remain a preregistered proper score. This is essential when market efficiency makes true edges small: accuracy thresholds and ROI slices are especially vulnerable to variance, selection effects, and post-hoc optimization.

---

## 4. Open/public NFL data ecosystem

### nflverse / nflverse-data

**Sources:**

- https://github.com/nflverse
- https://github.com/nflverse/nflverse-data

**Strengths:**

nflverse remains the preferred open foundation for chronology-clean football information: play-by-play, schedules, rosters, teams, player summaries, and related derived datasets can be accessed reproducibly. Its automated release infrastructure is valuable for team/player-state research and historical football features.

**LevLine implication:**

Use nflverse aggressively for football-state variables **when the release/timestamp semantics support the decision horizon**. It does not solve the M1 historical market-microstructure problem. The schedule odds used in prior LevLine research remain a late/closing benchmark whose exact fixed-horizon semantics are opaque for M1 purposes.

**Failure mode to avoid:**

Do not confuse a reliable football data source with a point-in-time sportsbook quote archive. Different provenance questions apply.

---

### `bobby-king3/nfl-market-movement-tracker`

**Source:** https://github.com/bobby-king3/nfl-market-movement-tracker

**What it provides:**

The public project documents an ELT pipeline built from The Odds API with approximately 1.8M+ rows, 30+ operators, spreads/totals/head-to-head markets, and 636 snapshots over the 2025–2026 NFL season. The project states that it pulled historical odds four times per day and provides line-movement marts in DuckDB/dbt.

**LevLine implication:**

This is valuable for:

- validating schemas;
- verifying book/market field behavior;
- studying coarse market movement;
- prototyping capture normalization;
- adversarial testing of joins and bookmaker identity.

It is **not** a scientifically clean replacement for a dense fixed-horizon 2020–2025 M1 panel. Four fixed daily captures can cause T-120, T-60, and T-30 to inherit the same stale quote. The repository’s own M1 audit correctly refused to relabel that cadence as dense near-kick microstructure.

**Key lesson:**

Exact timestamps do not imply fresh fixed-horizon observations.

---

### The Odds API historical snapshots

**Sources:**

- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/historical-odds-data/

**Documented semantics relevant to LevLine:**

The provider documents historical featured-market snapshots from June 6, 2020, at 10-minute cadence historically and 5-minute cadence from September 2022. The historical endpoint returns the closest snapshot **equal to or earlier than** the requested timestamp.

**LevLine implication:**

Those semantics map unusually well to M1’s frozen at-or-before selector. This is why the repository ranks The Odds API historical archive as the first commercial fallback for a coherent historical M1 panel.

**Governance implication:**

No purchase is authorized by this roadmap. If a future purchase is explicitly approved, qualification must be bounded, outcome-blind, and performed before M1 target scoring. The program should generate the exact timestamp request manifest first rather than buying an open-ended archive.

---

## 5. What the open-source review does *not* justify

The research scan does not identify a public GitHub repository whose model should simply be copied into LevLine ATS. The recurring weaknesses of public betting-model repositories are exactly the weaknesses the LevLine governance is designed to prevent:

- unclear timestamp semantics;
- closing lines used as if they were available earlier;
- random train/test splits instead of chronological evaluation;
- feature construction using final or revised data;
- accuracy/ROI reporting without a strong market-null proper-score comparison;
- unreported multiple testing;
- no immutable preregistration;
- no mechanism ablations;
- no prospective evidence.

Open-source value is highest at the **data engineering, reproducibility, and implementation-pattern** layer. A repository is not evidence of predictive edge because it contains sophisticated code or an attractive backtest.

---

## 6. Model-family synthesis after the literature review

### State-space / regularized dynamic market models

**Research value:** high only when paired with real timestamped multi-book state.  
**LevLine status:** already instantiated conceptually and preregistered as M1.  
**Decision:** execute M1; do not create an architecture-first duplicate.

### Dynamic team-strength / hierarchical football state

**Research value:** useful for football forecasting generally.  
**LevLine ATS status:** historical Frontier M3 did not add information beyond the market and its QB component hurt.  
**Decision:** do not reopen without a genuinely new point-in-time information mechanism.

### Discrete/key-mass margin distributions

**Research value:** high for probability representation because NFL margins concentrate at scoring-relevant integers.  
**LevLine status:** the simpler key-mass component explained the M4 gain and has already moved into `FV3-PROS-KMASS-01`.  
**Decision:** preserve the V3 prospective test; do not tune key masses against future outcomes.

### Joint-score / bivariate score modeling

**Research value:** plausible for richer distributional representation of total, margin, and covariance.  
**LevLine status:** JSIP V1 failed numerically before target scoring, so the mechanism remains unanswered.  
**Decision:** a tail-safe successor is a legitimate new historical representation study, but it must face the strongest market-only null and is lower priority than M1/V3 because it adds representation rather than new information.

### Direct classification / generic boosted residual models

**Research value:** low under the current information set because the analogous direct-CPL and market-residual experiments have already been rejected.  
**Decision:** a new library or learner is not sufficient novelty.

### Calibration / conformal uncertainty / selectivity

**Research value:** high for reliability and risk control after a survivor exists.  
**Decision:** downstream only. These methods cannot manufacture information that the input signal does not contain.

### Decision-focused betting optimization

**Research value:** appropriate only after probability quality is established.  
**Decision:** expected-value thresholds, Kelly sizing, and ROI optimization are Phase-G work, never a rescue step for a failed probabilistic model.

---

## 7. Integrated scientific inference

The combined external and repository evidence points to a narrower frontier than earlier ATS searches:

1. **The market is difficult to beat because it is already a powerful information aggregator.** That should be encoded as the baseline, not treated as an ordinary feature.
2. **Market instruments and market evolution can contain structure that one consensus spread discards.** LevLine has already confirmed a small moneyline-related distributional increment; rich dynamic market-state information remains open only through M1.
3. **Better representation can matter even when new information does not.** Key-number mass is the strongest current example and is already under prospective V3 governance.
4. **Complexity is not itself a research direction.** The failed football-state, residual, direct-classification, and static-shape experiments demonstrate that more expressive learners on the same inputs are unlikely to be the highest-value next experiment.
5. **Chronology and provenance are part of the model.** A backtest using the wrong market horizon is answering a different question no matter how sophisticated the algorithm is.
6. **Proper scoring, calibration, ablation, and prospective freezing are necessary because the expected edge is small.** They prevent random winner changes from being mistaken for sustainable predictive information.

## 8. Source-driven recommendation

The literature review therefore supports the same ordering as the repository evidence:

1. execute the existing M1 prospective market-state program exactly as frozen;
2. execute the existing V3 key-mass prospective program exactly as frozen;
3. retain M2 only as a point-in-time information-arrival experiment;
4. if a new historical candidate is required, prefer a **numerically corrected joint-score representation study** over another residual/threshold/football-feature model;
5. reopen historical M1 only after a coherent fixed-horizon market archive is qualified outcome-blind;
6. reserve calibration, conformal/selectivity, and betting economics for a model that first survives the proper-score gate.

That is the highest-information, lowest-redundancy use of the next ATS research cycles.