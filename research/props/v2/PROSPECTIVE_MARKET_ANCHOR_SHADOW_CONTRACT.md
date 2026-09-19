# LevLine Props 2.0 — Prospective Market-Anchor Shadow Contract

Status: **FROZEN BEFORE PROSPECTIVE SHADOW GRADES**  
Created: 2026-09-18  
Exact-source provenance amendment: 2026-09-19, before first prospective receipt

## Purpose

Start accumulating untouched prospective evidence for the strongest currently defensible Props 2.0
architecture before additional retrospective research can contaminate future evaluation.

This shadow layer does **not** alter the published V1 Fair Line, signal state, Sunday Signal product,
or official LevLine/F-ST winner model. It runs from an isolated research workflow after the live
Props workflow completes and persists only to `research-data/props-v2-prospective-shadow`.

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
- the source is the exact audit artifact from a successful **main-branch** `LevLine Props live refresh`;
- the source workflow run and source head SHA are preserved in the receipt;
- the source head SHA already contains this prospective listener/config (no retrospective backfill);
- the source V1 forecast has a stable `forecast_id`;
- the source forecast was recorded pregame;
- the shadow receipt itself is recorded before kickoff;
- prop type is a supported two-way line market;
- original V1 P(over) is finite and in [0,1];
- original market no-vig P(over) is finite and in (0,1);
- the original market capture is pregame;
- no result/current-game information is present.

Started games fail closed. A candidate is never reconstructed after kickoff.


## Exact source-run boundary

The workflow-run trigger is only a notification. It may **not** read whatever forecast happens to be
on latest `main`.

For every capture:
1. resolve the triggering live workflow run through the GitHub Actions API;
2. require workflow name `LevLine Props live refresh`, branch `main`, and conclusion `success`;
3. require the source head SHA to already contain this prospective listener and frozen config;
4. check out that exact source head SHA;
5. download that exact workflow run's full audit artifact;
6. require exactly one source `forecasts.json`;
7. record receipts only from that artifact.

This prevents an overlapping or later live refresh from being mislabeled under an earlier trigger.

A live run whose source commit predates this exact-run listener cannot be replayed later and called
prospective evidence. Missing pregame receipts remain missing.

## Immutable identity

Every shadow receipt must preserve:
- source workflow run ID;
- source head SHA;
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

## Revalidation status

This isolated architecture remains the canonical replacement for #377. It is being revalidated after
the Props history/receipt QA harness was repaired on main; no shadow coefficient, eligibility rule,
or research boundary changes in this revalidation.
