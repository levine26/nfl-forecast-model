# Phase 1 Research Charter — ATS Next-Generation

**Phase:** 1 — Deep ATS Research, Problem Reformulation & Preregistration  
**Scope:** research/design/governance only  
**Production:** unchanged  
**Q1/Q2/Q3 execution:** prohibited

## 1. Question

Is it scientifically justified to replace the current ATS diagnostic framing — a point estimate of expected margin plus fixed Normal residual sigma — with a market-centered conditional distribution framework that explicitly estimates quantiles, conditional variance, discrete scoring mass, pushes and cover probabilities?

Phase 1 answers only whether/how to test that hypothesis. It does not answer whether the candidates work.

## 2. Prior evidence accepted without rescue

This phase accepts all prior negative results in `research/spread-points-nextgen/`, including the reproduced margin/market errors, 48.77% raw model-side ATS rate, failure of large disagreement as an edge, A0/B0/C0 results, and Candidate 5 rejection.

Mean market-residual stacking has already been tested. Q1 is allowed only because quantile loss targets a different estimand: conditional tail/median structure around the line.

## 3. Research conclusions that change the working proposal

1. The Dmochowski PLOS ONE result supports modeling conditional quantiles around a sportsbook proposition, but the paper's 0.476/0.524 thresholds correspond to a continuous/no-push payout idealization. NFL whole-number spreads require explicit push mass and exact quoted-price EV.
2. NFL margins are integer-valued and scoring-mechanism-dependent. A continuous fixed Normal bridge cannot represent push probability or excess mass at key margins.
3. Open-source `nfelotranslation` provides a reproducible example of a generalized-normal base, integer PMF, key-number excess and season-forward fitting. Its architecture is informative; its fitted parameters are not imported.
4. `nfl-bet-engine` demonstrates the potential complementarity of a simulated distribution and a direct ATS head, but its current code also illustrates why this program must treat pushes explicitly, avoid outcome-blind top-decile claims as validation, and keep calibration/selection chronology auditable.
5. Historical side juice, book identity and timestamps are not currently qualified across LevLine's 2022–2025 development surface. Exact historical quoted-price EV therefore cannot be fabricated. Price-aware/multi-book extensions are prospective unless a revision-safe historical source is later qualified under a new preregistration.
6. Current public David Sasser pages continue to expose projected scores, projected line, open/current line and ATS picks, but no public reproducible model specification or source code was located. Only the observable separation of model projection from market comparison is transferable.

## 4. Exactly three primary Phase-2 experiments

Phase 2 is frozen to Q1/Q2/Q3 as documented in the dedicated preregistrations. No fourth learner, boosted-tree rescue, neural architecture, player-state reconstruction or arbitrary ensemble may be added without a new version and pre-result governance amendment.

## 5. Compact feature principle

V1 tests whether the **ATS/distributional formulation itself** adds value. It uses a compact set of already-available PIT-safe team state plus market variables. New historical personnel, injury, news and weather reconstruction is intentionally excluded from the primary candidate family.

## 6. Market timing family

Historical nflverse schedule line/moneyline/total fields remain an **opaque closing/late benchmark**, not T-120 and not a named book. They must never be mixed semantically with prospective `market_t120` snapshots.

Prospective timestamped multi-book data may be collected and qualified outcome-blind, but cannot retroactively redefine historical rows.

## 7. Stop/abort rules for Phase 2

Stop and quarantine the affected experiment if any of these cannot be proven:

- spread sign and grading convention;
- exact market snapshot semantics;
- target row uses only prior-time fitted parameters;
- key-number mass uses only prior training history;
- model/feature hyperparameters are selected only inside inner chronology;
- optional market price belongs to the same side/line/book/timestamp being evaluated;
- completed 2026 outcomes are excluded from candidate design/selection;
- duplicated games and pushes are handled deterministically.

## 8. Scientific disposition after Phase 3

The only permitted research dispositions are:

- `REJECTED`;
- `INCONCLUSIVE`;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

Historical development evidence alone cannot produce `PROMOTE` or alter production.