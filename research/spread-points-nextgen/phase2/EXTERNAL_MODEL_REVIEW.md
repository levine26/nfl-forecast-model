# Phase 2 — External Model and Public-System Review

**Status:** design research only  
**Purpose:** identify transferable architecture, not copy external weights or accept self-reported performance at face value.

## Evaluation dimensions

Each external system is reviewed on:

- prediction target and outputs;
- architecture;
- data inputs;
- team-strength methodology;
- market use;
- QB/player treatment;
- scoring-process treatment;
- calibration / uncertainty;
- validation design;
- prospective evidence;
- chronology / point-in-time transparency;
- reproducibility;
- transferable concept;
- limitations.

Evidence is explicitly classified as peer reviewed, strong technical research, reproducible open source, practitioner/industry evidence, or speculative/opaque.

---

## 1. David Sasser — davidsasser.com

**Public product:** https://www.davidsasser.com/cfb

The current public college-football board exposes, game by game:

- projected score for each team;
- a projected model line;
- opening market line;
- current market line;
- ATS selection;
- aggregate straight-up / ATS tracking;
- a page-level update timestamp for the current weekly board.

The graphic view separately publishes projected line and model pick.

### Four-way evidence classification

#### 1. Reproducible methodological evidence

**None located in the public materials reviewed for Phase 2.**

No public source located in the review supplied enough information to reconstruct the forecast from raw data or independently reproduce the reported historical record.

#### 2. Technical but incomplete information

The public board proves that Sasser maintains distinct objects for model-projected team scores, model-implied line, opening line, current line and the final displayed market-side pick. That is technically informative about output semantics, but it does not reveal:

- training data;
- feature construction;
- estimator/model family;
- parameter estimation;
- chronology or revision policy;
- whether market data enter the score projection itself;
- point-in-time source capture;
- walk-forward tuning;
- frozen candidate identity.

A current-week update timestamp is useful product metadata but is not an immutable historical forecast archive.

#### 3. Product-design observations

The strongest transferable concept is **surface separation**:

`model score -> model line -> market comparison -> displayed selection`

That is directly relevant to LevLine because current Sunday Signal already contains separate independent score/margin/total objects, F-ST winner probability and a probability-implied public spread. Phase 2 adopts the semantic separation, not Sasser's unknown model.

#### 4. Unsupported performance / marketing claims

The board displays aggregate straight-up and ATS records. Phase 2 does **not** treat those records as scientific evidence because the public material reviewed does not establish an independently frozen forecast archive, denominator policy, point-in-time market source, model version history or selection/tuning protocol.

### LevLine use

Adopt the score-versus-line-versus-market semantic separation. Require LevLine to exceed the public Sasser product in provenance, fixed candidate identity, same-horizon labeling and reproducibility. Do not copy coefficients, infer hidden methodology from outputs, or use the displayed public record as evidence that a challenger should survive.

---

## 2. nfelo

**Public site:** https://www.nfeloapp.com/  
**Open-source repository:** https://github.com/greerreNFL/nfelo

nfelo is a particularly useful comparator because its code and design are publicly inspectable.

### Relevant architecture

**Evidence class:** reproducible open source / practitioner technical evidence.

The current open-source implementation includes:

- Elo-style evolving team strength;
- home/rest/context modifiers;
- QB adjustment;
- blended game-outcome signals including margin and weighted EPA;
- preseason priors;
- an explicit raw-model versus market-regressed distinction;
- separate open and close market regression;
- translation from line/strength into probabilistic outcomes.

The market-regression implementation uses a nonlinear disagreement-based pull plus open-to-close movement adjustment and a residual cap.

### Transferable lessons

1. Keep a **football-only base** separately measurable.
2. Treat market regression as a **second layer**, not a hidden model input.
3. Market-aware optimization can degenerate toward copying the market.
4. Dynamic team strength can combine scoreboard and efficiency information.
5. QB context can be useful but should not be treated as isolated individual talent.
6. NFL margin distributions have key-number structure that a Normal approximation misses.

### What LevLine will not copy

- current nfelo parameter values;
- proprietary/PFF inputs;
- nonlinear market-regression rules before a simpler residual model is tested;
- any ATS-based tuning objective;
- closing-line results relabeled as a different forecast horizon.

### Phase 1 interaction

Phase 1 found that larger LevLine-market margin disagreements become less reliable. That makes an adaptive `trust the model more when it disagrees more` rule especially inappropriate as a starting assumption. LevLine first tests a regularized residual forecast around the market.

---

## 3. Open Source Football / nflverse ecosystem

Representative technical references:

- opponent-adjusted EPA:
  https://opensourcefootball.com/posts/2020-08-20-adjusting-epa-for-strenght-of-opponent/
- multilevel team ability from EPA:
  https://opensourcefootball.com/posts/2021-06-27-estimating-team-ability-from-epa/
- rolling EPA prediction:
  https://opensourcefootball.com/posts/2020-12-29-exploring-rolling-averages-of-epa/

### Transferable lessons

- raw EPA needs regularization;
- schedule/opponent strength can distort naive team ratings;
- opponent adjustment should be lagged;
- uncertainty matters;
- simple public-data approaches can be reproduced within LevLine's $0 constraint.

### Caveat

These are technical demonstrations, not a guarantee that a specific adjustment generalizes to current NFL score prediction.

### LevLine use

Use nflverse data as the main public-data foundation for Challenger A and B. Test opponent adjustment as part of a coherent latent-strength model rather than as dozens of standalone transformed columns.

---

## 4. Drive / score-process public systems

Public technical work on drive outcomes, expected points and scoring simulation shows a coherent decomposition:

`possessions -> drive state/outcome -> points -> score distribution`

This structure is attractive because Phase 1 found an unusually narrow total forecast distribution and difficulty distinguishing highly asymmetric games.

### Transferable lessons

- model game volume separately from efficiency;
- score outcomes are discrete;
- offensive and defensive contribution should be separated;
- simulation can produce coherent home score, away score, margin, total, win, cover and over probabilities.

### Caveats

- play/drive models can become data-hungry and overfit;
- same-game realized process variables cannot leak into pregame forecasts;
- more components create more estimation error.

### LevLine use

Only one bounded Challenger B is authorized: expected possessions plus regularized per-drive scoring distributions. No full play-by-play sequence simulator is preregistered.

---

## 5. FiveThirtyEight-style Elo / QB concepts

Traditional Elo provides an interpretable dynamic team-strength baseline, and public QB-Elo approaches motivate separately updating quarterback value.

### Transferable lesson

Separate persistent team strength from shorter-lived quarterback/start-state changes.

### LevLine limitation

Historical starter identity is not uniformly point-in-time qualified across 2022–2025. A QB layer is therefore conditional rather than mandatory in the initial challenger set.

---

## 6. External-system comparison matrix

| System / family | Reproducible? | Market dependence | PIT transparency | Strongest transferable idea | LevLine status |
|---|---|---|---|---|---|
| David Sasser public CFB board | Low from public materials | Market shown separately | Insufficiently documented | score -> projected line -> market comparison separation | design comparator only |
| nfelo | High / open source | explicit market-regression layer | mixed by data source; architecture visible | separate base model and market regression; dynamic rating | strong technical comparator |
| nflverse / Open Source Football EPA models | High | football-only | good when lagged as shown | opponent adjustment + multilevel shrinkage | direct design input |
| peer-reviewed state-space football models | method reproducible | football-only | historical datasets | dynamic latent team strength | primary statistical foundation |
| expected-points / player-value research | medium-high | football-only | depends on implementation | multilevel process/player modeling | conditional component evidence |
| drive-outcome public models | medium | usually football-only | implementation-dependent | possession / drive decomposition | Challenger B inspiration |

---

## 7. External-model conclusion

No reviewed public system supplies a ready-made LevLine successor.

The strongest transferable combination is:

1. Glickman/Stern-style dynamic strength;
2. nflverse-style opponent-adjusted efficiency;
3. a separate market-residual layer;
4. one bounded drive/possession challenger;
5. coherent predictive distributions;
6. transparent score-versus-market product semantics similar to the useful part of davidsasser.com.

The shortlist remains intentionally smaller than the universe of interesting public ideas.

## 8. David Sasser deep-search closeout

A second targeted public-web review was performed for \`davidsasser.com\` using methodology/model/source-code/archive/interview/validation terms in addition to the live CFB board and its graphic view.

### What was actually located

1. **Product-design observation — directly inspectable**
   - the public CFB board displays model-projected team scores;
   - a model projected line is shown separately from opening/current market lines;
   - a model pick and tracking surface are displayed separately.
   - public pages inspected: https://www.davidsasser.com/cfb and https://www.davidsasser.com/cfb/graphic

2. **Technical but incomplete information**
   - the visible forecasts imply a score-to-line comparison workflow;
   - the public surface is not sufficient to identify the statistical estimator, priors, features, training window, market ingestion rule, or recalibration procedure.

3. **Reproducible methodological evidence**
   - **none located in the public material found during Phase 2**.
   - targeted searches did not surface public source code, a complete technical specification, an independently reproducible fixed-horizon forecast archive, or a documented rolling-origin validation protocol.

4. **Unsupported / non-transferable performance claims**
   - any displayed or self-reported records are treated as product metadata only unless the underlying forecast timestamps, selection rule, denominator, and frozen history can be independently reconstructed.

This is an evidence-of-search statement, not proof that no private or unindexed methodology exists.

### Transfer rule

The only concept imported from Sasser is the **semantic decomposition**:

\`football score projection -> model line -> market line comparison -> downstream selection/tracking\`

No coefficient, record, claimed advantage, feature, or tuning policy is imported.

### Comparison with transparent systems

This is why nfelo and Open Source Football carry more methodological weight in Phase 2: code/method details are publicly inspectable. Sasser remains useful, but in a different evidence category.

## 9. External-model red-team conclusion

The review does **not** justify adding another challenger.

The strongest external lesson is architectural restraint:

- dynamic team strength deserves one bounded football-only reference;
- a drive model deserves one structurally separate reference;
- market regression deserves an explicit market-null hierarchy;
- public model records without reconstructable chronology do not justify model expansion.


---

## 10. Full external-system evidence matrix

| System | Prediction target | Architecture / team strength | Inputs | Market use | QB/player treatment | Scoring-process treatment | Calibration / uncertainty | Validation design | Prospective evidence visible? | Reproducibility | Transferable idea | Principal limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| David Sasser CFB | team scores, projected line, ATS pick | not publicly specified | not publicly specified | opening/current lines displayed separately | not publicly specified | score projections visible; internal process opaque | not disclosed | aggregate record shown; independent chronology not reconstructable | current board is timestamped, but full immutable archive not established | **low for methodology** | score -> model line -> market comparison separation | opaque model/data/tuning |
| nfelo | team rating / line / win probability | dynamic Elo-style rating with efficiency/context adjustments | public results/efficiency plus configured context | explicit opening/closing regression layer | QB adjustment present | not a full drive simulator | probability translation; market regression code visible | code inspectable; external data PIT varies | public weekly outputs exist, but this review does not treat them as an independent prospective trial | **high architecture/code** | football base separate from market regression | practitioner system; some data/parameters not independently validated |
| Open Source Football / nflverse examples | team ability / EPA-derived ratings | multilevel / opponent-adjusted EPA examples | nflverse/nflfastR PBP | generally football-only | varies by post | play/EPA process | uncertainty in multilevel examples | technical demonstrations; chronology inspectable when lagged | not generally a frozen forecasting product | **high code/data reproducibility** | lagged opponent adjustment + shrinkage | posts are not proof of score-forecast superiority |
| FiveThirtyEight-style Elo/QB concepts | win probability / rating | Elo + QB adjustment | results + QB performance | historically market-comparable | explicit QB state | no drive simulator | probability output | historical public methodology; current product discontinued | no current prospective product | **medium** | separate persistent team state from shorter-lived QB state | unified LevLine PIT starter history is absent |
| Glickman/Stern family | NFL scores | latent time-varying team strength | historical NFL scores/context | none in base | player shocks absorbed into state movement | direct score model | state uncertainty | predictive historical study | no modern live archive | **method reproducible** | dynamic partial pooling | older era |
| Baker/McHale family | exact NFL scores | score-event point process | prior-game team stats and/or market | optional spread/total inputs | indirect through team stats | **explicit scoring hazard/process** | full exact-score distribution | genuine OOS evaluation | historical paper only | **method reproducible** | discrete football scoring distribution | older data environment |

## 11. Systems deliberately not promoted into the shortlist

Phase 2 located additional public repositories and hobby/technical NFL models. They were not added as design authorities merely because they use modern ML.

Common disqualifiers were:

- hyperparameter search without a clearly protected temporal holdout;
- winner-only targets rather than team points/margin/total;
- unclear or hindsight feature construction;
- no prospective record;
- opaque data licensing;
- no evidence that complexity beats a simpler baseline.

This is a deliberate negative finding. The review favors a small number of sources with either strong peer-reviewed methodology or unusually transparent reproducible architecture.

## 12. External-review conclusion after red team

The external review does **not** justify expanding beyond A0/B0/C0.

It strengthens three constraints instead:

- dynamic/partial-pooling structure should be tested simply first;
- football scoring discreteness deserves one bounded process model, not a simulator zoo;
- market-aware modeling must retain an explicit market-only null and must not hide market dependence.

David Sasser remains useful as a product-semantic comparator, not a scientific benchmark.
