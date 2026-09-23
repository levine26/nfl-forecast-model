# Open-Source Model Review

Review date: 2026-09-23

Evidence classes used here: **1** peer-reviewed; **2** reproducible open source; **3** strong technical practitioner; **4** opaque product/system; **5** speculative.

## `greerreNFL/nfelo` — class 2

Inspected source commit: `e3750167bc456551ea626e68b48986169c49d3e7`.

### What the code actually does

The current `Nfelo.py` implementation integrates a market-aware Elo model with `nfelotranslation`. It maintains explicit sign translations between its internal home-favorite convention and sportsbook spread convention, regresses forecasts toward market observations, and uses the translation layer for cover/push/loss probabilities. Its evaluation logic distinguishes opening/closing market information and computes CLV/EV-style outputs.

### Transferable concepts

- explicit sign-convention boundaries and tests;
- market as a powerful prior/benchmark;
- translate one coherent margin distribution into cover/push/loss rather than inventing separate ad-hoc probabilities;
- distinguish open/current/close market horizons;
- season-aware distribution translation;
- preserve push as its own outcome.

### Not transferred

- current nfelo market-regression coefficients;
- current margin-distribution parameters;
- any reported betting performance;
- fixed -110 assumptions as universal economics.

LevLine must learn its own parameters under its own frozen chronology.

## `greerreNFL/nfelotranslation` — class 2

Inspected source commit: `5cf05b54063e10085146e358e91b90193f1ef8c5`.

### `MarginDistributionModel`

The implementation constructs a discrete probability mass function over integer NFL margins on a bounded support, combines a continuous base distribution with explicit key-number adjustments, normalizes it, and exposes spread/probability translations.

### Base distribution

`BaseDistribution.py` uses SciPy's generalized normal distribution. Gaussian behavior is the beta=2 case; lower beta values can generate heavier tails. Distribution parameters are season/version aware rather than assumed permanently stationary.

### Normalization and pushes

The normalizer explicitly distinguishes integer and half-point spreads. Integer spreads can assign mass to an exact push; half-point spreads cannot. This is exactly the structural distinction missing from a continuous fixed-Normal bridge.

### Transferable concepts

- integer PMF as the canonical object;
- explicit key-number excess mass;
- continuous-base-to-discrete-bin integration;
- normalization after key adjustments;
- season/regime awareness;
- deterministic cover/push/loss translation from the PMF.

### Deliberate LevLine differences

Q2 does not copy the package's fitted parameters or unrestricted fitting choices. It freezes a small base-family comparison, a fixed key set, a modern-era floor, and chronology-clean estimation. Q2 also explicitly tests conditional scale from market spread/total state.

## `ShamgarBN/nfl-bet-engine` — class 2 implementation, reported performance class 3 at best

Inspected source commit: `9aa4326c96d6aa5d771b7b68be8226d9f96a7023`.

### Architecture observed

The repository combines:

- a score-model/simulation path;
- a direct ATS classifier;
- probability calibration;
- an ensemble of distribution-derived and direct probabilities;
- walk-forward-style evaluation claims and betting-selection logic.

This supports the architectural hypothesis that a score/distribution model and a direct ATS head may contain complementary information. It does **not** validate the reported edge for LevLine.

### Methodological weaknesses found in source

1. The direct ATS path removes pushes rather than treating them as a structural third outcome.
2. Isotonic calibration is fit on predictions from the same training sample used to fit the classifier, creating optimism relative to a truly out-of-fold calibration protocol.
3. README descriptions and implementation details, including ensemble weights, are not fully stable across code/documentation.
4. The EV helper is not a sufficient contract for varying American odds and should not be copied as LevLine economics.
5. Flexible boosting plus calibration plus selective thresholds creates substantial researcher degrees of freedom if not preregistered.

### LevLine transfer

Transfer only the **question**: does a direct ATS probability head add information beyond a score/distribution path? Q3 answers that under a bounded learner set, true OOF calibration, explicit pushes and no ROI-based tuning.

## `nflverse` ecosystem — class 2

LevLine already relies on nflverse-style public NFL data infrastructure. It is appropriate for schedules, play-by-play-derived team state, scores and generic historical market fields. It is **not** assumed to provide historical book-specific spread-side juice and timestamps simply because it contains `spread_line`, `total_line` and moneyline fields.

Transfer: reproducible football data and stable IDs. Limitation: historical market microstructure provenance is insufficient for book/price-sensitive claims without an additional source.

## `dmochow/optimal_betting_theory` — class 2 paired with class-1 paper

The PLOS ONE paper directly links its reproduction code. This is unusually strong evidence because the theoretical ATS/quantile argument has both peer-reviewed exposition and public implementation materials.

Transfer: quantile decision formulation and caution against post-hoc profitable-bin selection. LevLine still uses a discrete push-aware economics contract rather than the paper's zero-push continuous simplification.

## Broader GitHub search

A broad repository search for NFL betting models surfaced numerous projects such as `slieb74/NFL-Betting-Data`, `w1r2p1/nfl_betting_market_analysis`, `brianbailey18/NFL-Betting-Models`, and other prediction/betting repositories. A separate Bayesian/NFL-score search produced little maintained NFL-specific distributional infrastructure beyond isolated projects.

These additional repositories were not elevated into Q1-Q3 because search visibility, notebooks or performance claims are not a sufficient scientific reason to expand the preregistered model family. The central reusable concepts they represent—market data acquisition, feature engineering, classification, simulation and historical betting summaries—are already covered by stronger evidence above. They remain discovery references, not parameter/model-selection authorities.

## David Sasser comparator — class 4 for methodology

`davidsasser.com` was revisited. Public matchup/board pages visibly expose projected scores/spread, opening/current market line, ATS decision surfaces, and football diagnostics such as efficiency, success, pass/rush, explosiveness, havoc, finishing drives and pace.

A public GitHub presence was also checked. No public repository or technical document was found that establishes the hidden methodology powering the betting projections. Observable page design should not be reverse-engineered into unsupported claims.

Transferable observable concepts only:

- side-by-side model line versus open/current market;
- compact explanatory matchup diagnostics;
- historical tracking/accountability;
- explicit separation of projection and ATS decision.

Not transferable: unseen model weights, training method, claimed edge, or proprietary data assumptions.

## Phase-1 conclusion

The strongest open-source contribution is not a magic parameter set. It is an architecture discipline:

1. one explicit market sign convention;
2. one coherent discrete margin distribution;
3. explicit key-number/push probability;
4. chronology-clean probability calibration;
5. a separate direct ATS head only if it improves proper scoring;
6. optional blending selected strictly on prior OOF log loss.

That architecture is scientifically worth testing, but no external repository supplies evidence sufficient to bypass LevLine's own market nulls or prospective confirmation gate.