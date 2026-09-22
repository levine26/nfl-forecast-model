# Phase 2 — Feature Hypotheses and Player/Personnel Policy

**Status:** preregistered design map  
**Purpose:** constrain Phase 3 implementation to a small number of mechanistically justified, point-in-time-safe inputs.

## 1. Feature admission rule

A feature family is eligible only when all five are documented:

1. football mechanism;
2. source and identity key;
3. decision-time / publication-time rule;
4. missingness policy;
5. candidate/ablation role.

No feature is admitted solely because it correlates with historical outcomes.

---

## 2. Fixed lagged-state rule

Unless a feature is explicitly defined otherwise in `BOUNDED_IMPLEMENTATION_SPEC.md`, initial A0/B0/C0 team-process summaries use only prior completed regular-season team games and an exponentially weighted mean with a **fixed 8-team-game half-life**.

This removes rolling-window selection from Phase 3.

## 3. Team strength / efficiency

| Feature family | Mechanism | Source | PIT rule | Initial role |
|---|---|---|---|---|
| offensive EPA / play | latent scoring efficiency | prior completed-game nflverse PBP | shifted before current game | Challenger A/B core |
| defensive EPA allowed | opponent suppression | prior completed-game nflverse PBP | shifted | Challenger A/B core |
| pass EPA | QB/pass-game efficiency | prior PBP | shifted | A optional sub-state |
| rush EPA | run-game efficiency | prior PBP | shifted | A optional sub-state |
| success rate | down-to-down consistency | prior PBP | shifted | A/B |
| opponent-adjusted offense/defense | correct schedule strength | derived from prior PBP only | outer-fold training only | A primary hypothesis |
| sequential Elo / latent prior | persistent team state | internal sequential model | pregame state only | A reference/prior |

**Expected role:** reduce favorite/blowout compression by representing opponent-adjusted strength more directly.

---

## 4. Pace / possession

| Feature family | Mechanism | Source | PIT rule | Role |
|---|---|---|---|---|
| offensive plays / drive counts | game volume | prior PBP | shifted rolling/dynamic state | B core |
| neutral pace | avoid game-script contamination | prior PBP | only prior plays; definition fixed | B optional |
| possession/drive duration proxies | opportunities to score | prior PBP | shifted | B optional |

Phase 1 found that a crude prior-five play-count proxy alone has almost zero simple correlation with absolute error. Therefore Challenger B must test a **structural possession model**, not merely add one pace column to the existing regression.

---

## 5. Scoring-process variables

| Feature family | Mechanism | PIT | Role |
|---|---|---|---|
| red-zone opportunity rate | scoring opportunities | lagged prior games | B |
| red-zone TD/FG conversion | scoring efficiency | lagged, regularized | B |
| explosive-play rate | shortens drives / increases score tails | lagged | B |
| sack rate | drive-ending pressure | lagged | B |
| turnover rate | empty/short-field possessions | lagged with shrinkage | B |
| field-goal attempt / conversion state | 3-point scoring frequency | lagged | B |
| defensive/special-teams scoring | rare scoring tail | historical base rate / simple residual component | B optional |

Do not model rare events with unconstrained team-specific parameters unless sample support is adequate.

---

## 6. Home field / rest / travel

### Initially allowed

- home indicator / dynamic league home-field parameter;
- rest differential;
- deterministic divisional indicator if used only in a prespecified sensitivity.

### Conditional

- travel distance / time-zone shift, only if venue mapping is exact and deterministic;
- surface/roof if game venue is reliably mapped.

Do not launch a large interaction search across stadium/context fields.

---

## 7. QB policy

### Football mechanism

QB quality can materially shift dropback efficiency and scoring, but team/scheme effects make naive individual point adjustments unstable.

### Eligible input structure

If a PIT-safe expected starter is available:

- starter prior EPA/dropback or shrinkage-based quality;
- prior starts / dropbacks;
- continuity with current team;
- starter-change flag;
- replacement delta relative to team/QB baseline;
- uncertainty / missingness flag.

### Historical blocker

Final schedule starter identity is not sufficient evidence of what was known at a simulated earlier horizon.

The current repository does not yet have a unified 2022–2025 qualified fixed-horizon starter history.

### Policy

QB features are **not required for initial A/B/C selection**.

They may be tested only as:

1. a later prespecified historical sensitivity on genuinely qualified rows; or
2. prospective shadow features.

No missing starter is encoded as “same starter.”

---

## 8. Injury / offensive-line / personnel policy

The 2025 qualified practice-state composite is one-season evidence only.

Potential mechanisms:

- pass protection;
- target/carry concentration;
- offensive-line continuity;
- pass-rush/secondary availability;
- replacement quality.

But simple counts of “questionable” or “limited” players are not presumed predictive.

### Historical rule

No unified multi-season injury feature is admitted until:

- as-of time is proven;
- stable player identity passes;
- expected role/replacement is defined;
- missingness is quantified.

### Prospective rule

Timestamped 2026+ snapshots may be graded prospectively but completed 2026 outcomes cannot decide the Phase 3 architecture.

---

## 9. Advanced player / charting inputs

Potential free sources:

- NGS weekly;
- FTN charting;
- PFR advanced.

These can describe prior game processes such as pressure, time to throw, motion, play action or separation only when:

- prior game is completed;
- source is known to have been published before the next forecast horizon;
- structural missingness is handled explicitly.

They are optional ablations, not core prerequisites.

---

## 10. Weather

Potential mechanisms:

- passing depth/efficiency;
- field-goal efficiency;
- turnover/fumble risk;
- play-calling / pace.

Historical realized weather is prohibited as a surrogate for a forecast.

Weather enters a candidate only after:

- exact venue coordinates are resolved;
- forecast issue/update timestamp is retained;
- forecast availability time <= simulated decision time.

Until then: blocked.

---

## 11. Market inputs

Challenger A/B: no market input.

Challenger C:

- spread/total at the defined historical market family;
- football-only predicted margin/total or latent strength features;
- optionally line level to allow regularized nonlinear residual patterns.

Do not include bookmaker outcome labels, future line moves, or closing data in an earlier-horizon model.

---

## 12. Feature-family priorities

### Tier 1 — required initial implementation
- dynamic offense/defense strength;
- opponent-adjusted efficiency;
- home/rest;
- possession/drive volume for B;
- drive scoring-process rates for B;
- market residual target for C.

### Tier 2 — prespecified diagnostics / amendment candidates
- pass/rush decomposition;
- sacks beyond the fixed B0 process state;
- simple static venue context;
- alternative red-zone/explosive formulations beyond the fixed B0 definitions.

The initial B0 red-zone, explosive and turnover states are fixed by `BOUNDED_IMPLEMENTATION_SPEC.md`; Tier 2 is **not** permission for Phase 3 to search alternate definitions after seeing development metrics.

### Tier 3 — conditional on data qualification
- QB starter/replacement;
- OL/personnel;
- advanced charting;
- weather;
- coaching/scheme changes.

This ordering is binding for the initial Phase 3 build.


## 13. Initial Phase 3 feature freeze

For avoidance of doubt, the initial implementation feature contract is:

- **A0:** the exact compact offense/defense EPA, pass-EPA, success, home and rest set in `BOUNDED_IMPLEMENTATION_SPEC.md`;
- **B0:** the exact independent drive-volume, team/opponent indicator, EPA/success, red-zone, turnover/takeaway, explosive, home and rest set in that specification; no A0 output enters B0;
- **C0:** the exact market/football residual feature set in that specification and `MARKET_RESIDUAL_SPECIFICATION.md`.

The broader tables in this document are a mechanism/source research map, not permission for Phase 3 to add every listed feature.
