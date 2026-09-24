# CANDIDATE RESEARCH CARDS

These are mechanism cards, not fitted models. No Frontier candidate target performance was generated in Phase 1.

## M1 — `FRONTIER-M1-DYNAMIC-MARKET-STATE`

**Mechanism:** multiple books and prices are noisy observations of a dynamic latent fair market state; disagreement, lead/lag, juice-only movement and movement breadth may preserve information lost by one static consensus spread.  
**Information source:** timestamped multi-book spreads + side prices + moneylines + totals + book identity/quote age.  
**Why incremental:** explicitly targets information inside the market process that prior LevLine representations discarded.  
**Target:** market-relative margin/cover distribution at a frozen horizon; exact Phase-3 target to be preregistered.  
**Required data:** historical quote snapshots with true timestamps and stable book IDs.  
**PIT feasibility:** promising via The Odds API / SportsDataIO / PropLine, unproven until Phase 2.  
**Supporting evidence:** sequential-line price-discovery studies; informed-trader line-movement literature; finance microstructure; nfelo market-regression practice.  
**Contradictory evidence:** efficient-market literature; Adaptive Candidate 3 did not establish independent simple path information.  
**Best model family:** robust latent-state/state-space estimator or small regularized microstructure model; final choice deferred.  
**Sample concern:** 2,000–3,000 games but many within-game quote observations; event-level inference must avoid pseudo-replication.  
**Leakage risk:** catastrophic if future/close quotes enter an earlier horizon.  
**Overfit risk:** high if dozens of books/path features are searched.  
**Falsification:** no proper-score gain vs same-timestamp market-level null, or path innovation adds nothing after level/juice/ML/total.  
**Novelty:** high relative to prior LevLine; prior C3 used a much simpler market path and lacked rich multi-book latent state.  
**Likely failure:** consensus market level already sufficient.  
**Minimum result to continue:** preregistered proper-score non-inferiority plus credible incremental improvement with uncertainty excluding practically meaningful harm; exact gate frozen Phase 3.  
**Red team — why it probably fails:** books copy/arb each other so cross-book observations are highly redundant; apparent lead/lag may be feed latency; market level may subsume nearly all usable path information.

## M2 — `FRONTIER-M2-PLAYER-STATE-DELTA`

**Mechanism:** timestamped expected lineup value changes may not be instantly/fully reflected in market state when player participation, role or starter identity is uncertain.  
**Information source:** player ability priors, practice/injury reports, depth charts, roster transactions, starter probabilities, expected role, replacement quality; market response at matching timestamps.  
**Why incremental:** focuses on information timing and uncertainty, not known injuries.  
**Target:** market residual / cover distribution conditional on contemporaneous market.  
**Required data:** reconstructable PIT player status and expected-role state, especially QB.  
**PIT feasibility:** moderate/uncertain; nflverse injury source break after 2024 is a major issue.  
**Supporting evidence:** nflWAR, sportsbook player point-spread value research, NBA player-absence price discovery, ESPN FPI public QB injury methodology.  
**Contradictory evidence:** closing markets appear to assimilate known absences well.  
**Best model family:** hierarchical player/unit value model + probabilistic participation/role layer; small event-level residual model.  
**Sample concern:** meaningful injury/starter events are sparse; position-level estimates can be weak.  
**Leakage risk:** final inactive/realized snap state is easily leaked.  
**Overfit risk:** many players/positions and event categories.  
**Falsification:** player delta becomes redundant once same-timestamp market move is included.  
**Novelty:** high; prior LevLine did not possess a complete PIT expected-lineup-value delta.  
**Likely failure:** market prices personnel faster/better than public data.  
**Minimum result:** event-time incremental proper-score signal that survives exclusion of QB-only or one-off events; exact gate Phase 3.  
**Red team:** public injury probabilities may be too slow/subjective, historical reconstruction may be impossible, and rare-event gains can be dominated by one headline QB injury.

## M3 — `FRONTIER-M3-HIERARCHICAL-STATE`

**Mechanism:** team/unit ability evolves as a latent stochastic process; fixed rolling windows blur changes and express no coherent uncertainty.  
**Information source:** chronology-safe PBP/team/unit performance, prior seasons, roster/QB state where feasible.  
**Why incremental:** better temporal filtering may detect real strength changes faster than fixed summaries.  
**Target:** market residual or latent margin component, always market-conditioned.  
**Required data:** mostly feasible through nflverse; roster transition PIT still matters.  
**PIT feasibility:** high for past game statistics, medium for detailed unit/personnel state.  
**Supporting evidence:** Glickman–Stern NFL state space; dynamic soccer/Bradley–Terry literature.  
**Contradictory evidence:** A0/B0/C0 show public football state has struggled to add information beyond market.  
**Best model family:** hierarchical state-space / dynamic linear or robust paired-comparison model.  
**Sample concern:** NFL seasons are short; unit decomposition can be weakly identified.  
**Leakage risk:** modest if game statistics are lagged correctly; higher with roster annotations.  
**Overfit risk:** process-noise/changepoint tuning.  
**Falsification:** no improvement over simple frozen rolling baseline after market conditioning.  
**Novelty:** medium; new temporal representation, not a new raw information source.  
**Likely failure:** market is a better dynamic state estimator than any public model.  
**Minimum result:** proper-score improvement attributable to dynamic-state ablation, not market leakage.  
**Red team:** this could become A0 with more elegant mathematics; if so it should die quickly.

## M4 — `FRONTIER-M4-DISCRETE-MARGIN-V2`

**Mechanism:** NFL final margins live on a discrete scoring lattice with pushes, key masses, heteroskedasticity and heavy tails; a valid conditional PMF can improve probability calibration near betting lines.  
**Information source:** historical margins + market state + any preregistered M1–M3 latent signals.  
**Why incremental:** mostly representation, not information; value is better probability translation/selectivity.  
**Target:** full integer margin PMF and derived cover/push/loss probability.  
**Required data:** highly feasible for scores/markets; exact dynamic conditioning inherits M1 data needs.  
**PIT feasibility:** high for outcome-training chronology; must prevent target-period reuse.  
**Supporting evidence:** Dmochowski decision theory; NFL key-number structure; nfelotranslation; distributional forecasting literature.  
**Contradictory evidence:** ATS-Q1/Q3 negative; key-number demand discontinuity does not imply return predictability.  
**Best model family:** tail-safe empirical/parametric discrete distribution with integer-bin integration and explicit key mass.  
**Sample concern:** conditional PMF cells become sparse quickly.  
**Leakage risk:** lower than M1/M2, but era/key-mass tuning can become target fishing.  
**Overfit risk:** high if many conditional key/tail terms are selected after results.  
**Falsification:** fails normalization/tail tests or does not improve proper score/calibration vs market-centered PMF.  
**Novelty:** high relative to invalid Q2 V1 numerical contract; experiment identity must be new.  
**Likely failure:** strong market-centered empirical distribution is already sufficient.  
**Minimum result:** clear proper-score/calibration improvement; ATS gains alone cannot continue it.  
**Red team:** it may only make probabilities prettier without adding any decision-relevant information; if so it is not a betting edge.

## Eliminated cards

- **Generic matchup-interaction booster:** rejected; plausible football interactions but no credible conditional-information mechanism and severe multiple-testing/sample risk.
- **Backdoor-cover/game-state simulator:** rejected as standalone; B0 already lost and no new PIT information source identified.
- **Deep-learning game predictor:** rejected; algorithm-first, sample-inefficient, no unique high-dimensional signal.
- **Static injury flags:** rejected; known absences are often priced by close.
- **Simple line-movement rule:** rejected; Adaptive C3 path result was not independent of market level.
- **Residual stacking / ensemble-only candidate:** rejected; Candidate 5 changed zero winners and combination requires complementary validated components.