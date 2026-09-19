# LevLine Props 2.0 — Prospective Market-Anchor Shadow Contract

Status: **FROZEN BEFORE PROSPECTIVE SHADOW GRADES**  
Created: 2026-09-18  
Branch: `research/props-v2-prospective-shadow`

## Purpose

Start accumulating untouched prospective evidence for the strongest currently defensible Props 2.0
architecture before additional retrospective research can contaminate future evaluation.

This shadow layer does **not** alter the published V1 Fair Line, signal state, Sunday Signal product,
or official LevLine/F-ST winner model.

## Shadow candidates

For every valid pregame two-way line-market V1 forecast, preserve two shadow probabilities.

### Candidate A — market-only baseline

```
P_over_market = original no-vig sportsbook P(over)
```

This is a comparator, not a LevLine model.

### Candidate B — market + frozen V1 residual

```
logit(P_over_shadow)
  = logit(P_over_market)
  - 0.0718941364380648
  + 0.0437506644681220
      * [logit(P_over_v1) - logit(P_over_market)]
```

The sportsbook coefficient is fixed at 1.0.

The two residual coefficients were fit once on all qualified pre-2026 historical V1 receipts after
the low-dimensional market-residual architecture had already been frozen. This fit is a final
pre-2026 training fit for **prospective shadow use only**. It is not itself untouched validation.

Training provenance:
- seasons: 2023–2025 regular season
- genuine Action Network OPEN historical population
- source V1 run: `35363701921`
- decided non-push training rows: 5,670
- 2023 forecast CSV SHA-256:
  `b89835c777fbef531afbdbadda3e07c6ac4da72b6a22178aa8dbc4e9ef29d4bd`
- 2024 forecast CSV SHA-256:
  `cf9e31d0e80cc141e47db3c4f6d167e52f66302e8e0085c16d8e9bfa0bb98e12`
- 2025 forecast CSV SHA-256:
  `6d2d8aaf95a549b1cc6841f23d49b07c3d9f9d38c1e7ee1be6242cced34d085a`

Frozen penalties used in the historical fit:
- residual beta L2 = 10.0
- intercept L2 = 1.0

No completed 2026 outcome was used to choose or fit these coefficients.

## Eligibility

A shadow receipt may be created only when:
- the source V1 forecast has a stable `forecast_id`;
- the source forecast was recorded pregame;
- the shadow receipt itself is recorded before kickoff;
- prop type is a supported two-way line market;
- original V1 P(over) is finite and in [0,1];
- original market no-vig P(over) is finite and in (0,1);
- the original market capture is pregame;
- no result/current-game information is present.

Started games fail closed. A candidate is never reconstructed after kickoff.

## Immutable identity

Every shadow receipt must preserve:
- source `forecast_id`;
- source forecast timestamp;
- source market capture timestamp;
- shadow recorded timestamp;
- player/game/prop identity;
- market line;
- original market probability;
- original V1 probability;
- market-only probability and side;
- frozen residual probability and side;
- challenger version;
- coefficient provenance;
- SHA-256 of the immutable source forecast when available.

A shadow identity is derived from the source forecast ID plus challenger contract/version. Rewriting
an existing identity with different contents is prohibited.

## Direction rule

For probability-based directional accuracy:
- P(over) > 0.50 => OVER
- P(over) < 0.50 => UNDER
- exactly 0.50 => no directional call

No edge-size threshold and no abstention based on historical profitability is authorized.

## Evaluation

After games finish, grade the immutable shadow receipts without changing originals.

Report separately:
- all decided non-push rows;
- market-only direction accuracy;
- market+V1-residual direction accuracy;
- frozen V1 direction accuracy;
- Brier score;
- log loss;
- calibration;
- by prop family;
- game-clustered uncertainty;
- closing-line/CLV comparison when source-qualified closes exist.

The central prospective question is:

**Does the frozen V1 residual improve on the market-only probability on untouched future games?**

## Contamination firewall

Once a shadow receipt is created, later 2026 results may be used only for evaluation. They may not
change:
- the coefficients above;
- feature selection;
- thresholds;
- family weights;
- calibration;
- challenger identity.

Any later challenger must receive a new version and begin a new prospective ledger.

## Promotion boundary

Neither candidate is production-authorized by this contract. Candidate A is explicitly a market
baseline. Candidate B remains a research challenger until a separate promotion gate is satisfied.


## Isolated execution amendment

The original implementation draft attempted to modify the live Props workflow and write the shadow
ledger into main. The research firewall correctly rejected that architecture.

The approved implementation pattern is now isolated:
- the production live Props workflow remains unchanged;
- a separate `workflow_run` research workflow executes only after a successful live refresh on main;
- it reads the already-published immutable `outputs/props/forecasts.json`;
- it records only still-pregame eligible rows;
- it persists the append-only ledger off main on
  `research-data/props-v2-prospective-shadow`;
- no Sunday Signal or published V1 artifact consumes that ledger.

This amendment changes deployment isolation only. The frozen candidate formulas, eligibility rules,
and pre-2026 fit provenance are unchanged.
