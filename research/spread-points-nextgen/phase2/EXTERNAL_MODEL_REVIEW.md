# Phase 2 — External Model and Public-System Review

**Status:** design research only  
**Purpose:** identify transferable architecture, not copy external weights or accept self-reported performance at face value.

## Evaluation dimensions

Each external system is reviewed on:

- target and outputs;
- data inputs;
- football-vs-market separation;
- chronology / point-in-time transparency;
- reproducibility;
- evaluation quality;
- relevance to Phase 1 residual failures.

---

## 1. David Sasser — davidsasser.com

**Public product:** https://www.davidsasser.com/cfb

The current public college-football board exposes, game by game:

- projected score for each team;
- a projected model line;
- opening market line;
- current market line;
- ATS selection;
- aggregate straight-up / ATS tracking.

### Transferable idea

The strongest transferable idea is **surface separation**:

`model score -> model line -> market comparison -> selection`

That is exactly the semantic clarity LevLine needs because current Sunday Signal already contains separate independent margin, independent total, F-ST winner probability and probability-implied public spread objects.

### Evidence limitations

Phase 2 search did not locate a sufficiently detailed public specification of:

- training data;
- feature set;
- model class;
- time-series validation;
- point-in-time market capture;
- exact historical forecast archive;
- tuning / selection policy.

Therefore:

- Sasser's public forecasts may be used as a design comparator;
- self-reported records are not LevLine validation evidence;
- no weights, coefficients or claimed edge are copied into the preregistration.

### LevLine use

Adopt the **separation of raw score projection from market comparison** as a product/research principle. Require LevLine to be more explicit than the public Sasser page about as-of data and reproducibility.

---

## 2. nfelo

**Public site:** https://www.nfeloapp.com/  
**Open-source repository:** https://github.com/greerreNFL/nfelo

nfelo is a particularly useful comparator because its code and design are publicly inspectable.

### Relevant architecture

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
