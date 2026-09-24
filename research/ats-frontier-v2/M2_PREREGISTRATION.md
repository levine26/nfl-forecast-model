# M2 PREREGISTRATION

## Identity

`FV2-PROS-M2-QBDELTA-01`

State: `PROSPECTIVE_ONLY`.

Broad 2022–2025 player/injury harmonization is not authorized and no historical Phase-4 M2 fit may be generated.

## Horizon

Primary prediction horizon: `T-120`.

Every status, depth, starter-probability and replacement-identity observation must have a publication/observation timestamp `<= T-120`.

## Mechanism

M2 is not `QB injured = 1`.

Define, conceptually:

`ExpectedQBValue = Ability * P(starts) * ExpectedRole + ReplacementValue * (1 - P(starts))`

The information signal is the change in expected QB value since the previous qualified state, measured against the contemporaneous change in the market.

## Frozen inputs

- lagged QB ability estimated only from games completed before the target;
- T-120 starter probability from timestamped practice/status/depth evidence;
- expected starter role probability;
- timestamped replacement identity;
- replacement quality from prior-only information;
- information-arrival timestamp;
- same-horizon market spread/price and change from the immediately preceding qualified market state;
- explicit missing/conflict indicators.

No same-game snap count, final inactive list, eventual starter identity, gamebook or completed target-game PBP may enter.

## Architecture

A hierarchical shrinkage QB-value model supplies ability/replacement estimates. The prospective event model is a ridge residual correction around the T-120 market state using only:

- change in expected QB value;
- market-implied change;
- their interaction/difference;
- conflict/missingness indicator.

No position-wide injury feature tournament is authorized.

## Null

The identical T-120 market state without QB-delta features.

## Metrics

Primary: paired multinomial cover/push/loss log loss versus market null.  
Secondary: Brier, calibration, and event-level concentration.  
ATS/ROI: diagnostic only.

## Required ablations

1. market only;
2. market + lagged QB ability level only;
3. market + full expected-QB-value delta.

The delta mechanism is not established if the full model's apparent gain is reproduced by ability level alone or is concentrated in one QB event.

## Failure / stop rule

Fail closed on missing publication timestamps or unresolved replacement identity. The broader M2 family is not revived from this QB-only identity without a new preregistered version.