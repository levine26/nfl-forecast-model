# LevLine Props 2.1 — Current State and Next Steps

Updated: 2026-09-21 / 2026-09-22 UTC

This is the canonical handoff for the next Props chat. Do not restart the project or re-audit old lanes unless new repository evidence requires it.

## 1. Frozen prospective cohort

The first clean Props 2.1 prospective cohort is immutable:

- source live workflow: `35477049179`
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- frozen receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- forecasts: **3,439**
- games: **15**
- players: **744**
- forecast week: **2026 Week 2**
- retrospective forecast mutation: **forbidden**

PR #458 is the canonical current-main evaluation surface. PRs #447, #448 and #457 are superseded.

## 2. First prospective result

The successful evaluation artifact from run `35662662103` graded:

- **1,606** forecasts
- **14** finalized games
- **349** graded players
- **359** like-for-like market-matched forecasts
- **193** players in the market-matched sample

This is one week and 14 finalized games. Under the preregistered minimum-sample rules it is a diagnostic/development cohort, not sufficient evidence for stable market-superiority, calibration, subgroup, or betting claims.

### Projection accuracy on the matched sample

- model-mean MAE: **11.770**
- Fair Line MAE: **11.983**
- original market-line MAE: **10.609**
- paired Fair-Line minus market absolute-error difference: **+1.375** model units
- game-clustered 95% CI: **[+0.828, +2.001]**

Positive paired difference means the frozen Props 2.1 Fair Line was less accurate than the original market line on this sample.

### Probability accuracy on the matched sample

- model Brier: **0.2707**
- market no-vig Brier: **0.2465**
- model-minus-market Brier difference: **+0.0243**
- game-clustered 95% CI: **[+0.0066, +0.0414]**
- model log loss: **0.7895**
- market no-vig log loss: **0.6860**
- model-minus-market log-loss difference: **+0.1035**
- game-clustered 95% CI: **[+0.0432, +0.1729]**

The frozen model therefore did **not** provide incremental probability accuracy beyond the matched original market on Week 2.

### Calibration diagnosis

Every preregistered fixed probability bin overpredicted realized hit rate:

- 50–55%: predicted **52.4%**, observed **43.7%**
- 55–60%: predicted **57.3%**, observed **32.4%**
- 60–65%: predicted **62.4%**, observed **47.6%**
- 65–70%: predicted **67.3%**, observed **53.7%**
- 70%+: predicted **84.2%**, observed **63.0%**

Expected calibration error: **0.1691**.

This is strong evidence of Week 2 overconfidence, but it must not be “fixed” and then validated on the same Week 2 cohort.

### Other important diagnostics

- zero original `MODEL EDGE` observations -> betting ROI is **not measurable**
- CRPS/PIT are unavailable because the frozen receipt did not preserve a lossless full distribution
- interval coverage is unavailable because the frozen receipt did not preserve a frozen interval
- 1,506 receipts could not be graded because required snap-participation evidence was missing
- 104 zero-offensive-snap rows were correctly voided
- the frozen cohort had overwhelmingly `UNKNOWN` role/workload states
- higher-volume and 6+ book subgroups showed especially large raw errors, but these are descriptive only and must not be cherry-picked as stable findings

## 3. Engineering state already completed

Do not redo these unless broken:

- full eligible-roster concentration semantics regression is merged (#434)
- point-in-time depth-chart transport into live Props 2.1 is merged (#446)
- depth-chart evidence remains categorical only; it does not assign workload or independently create a betting signal
- PropLine support and the shared public-demo fallback exist on current main
- the live Props publisher preserves immutable receipts/history and remains fail-closed on incomplete pregame state
- post-kickoff lifecycle no-op is being fixed in PR #459 so code-only pushes after the target week starts do not report false production failures

## 4. Scientific interpretation

The immediate objective is **not** to tune Week 2 until it looks good.

Week 2 is now a locked diagnosis/development cohort. Any successor model changed because of these findings must be assigned a new model/challenger version and evaluated on future untouched prospective data (Week 3+), or on a genuinely leakage-free historical reconstruction that was not used to select the change.

The current evidence says:

1. pure projections need better uncertainty/calibration;
2. personnel/workload state was too sparse in the frozen cohort;
3. the market remains a stronger matched baseline than Props 2.1 on Week 2;
4. recommendation logic should remain conservative until the model demonstrates incremental information prospectively.

## 5. Next execution plan — start here

### Lane A — calibration and distribution challenger

Create a new isolated challenger; do not edit the frozen 2.1 cohort.

Research and preregister:

- prop-family-specific shrinkage / hierarchical calibration;
- support-correct distributions for yards, receptions and TDs;
- probability tempering / uncertainty widening;
- calibration methods trained only on valid prior data;
- preservation of full simulated distributions and intervals in future immutable receipts so CRPS, PIT and coverage become measurable.

No Week 2 re-evaluation may be used as the validation result for the selected calibration change.

### Lane B — personnel and opportunity challenger

Build on merged #446.

Prioritize point-in-time evidence that can reduce `UNKNOWN` role/workload state:

- official injury reports and availability;
- depth-chart role;
- recent snap/route participation;
- starter/replacement state;
- projected route/carry/target opportunity;
- explicit uncertainty mixtures for questionable/returning/replacement players.

Keep availability and workload uncertainty probabilistic. Never infer pregame availability from eventual participation.

### Lane C — market microstructure / residual-information study

The scientific question is whether LevLine contains **incremental information beyond market**, not whether it can merely imitate the market.

Preregister a research-only residual study using:

- consensus line and no-vig probability;
- book count / liquidity;
- dispersion;
- line movement and price movement;
- forecast horizon;
- model-minus-market disagreement.

Keep the pure football forecast distinct from the market comparison layer. Do not leak closing information into the forecast.

### Lane D — prospective collection

Before the next untouched slate:

- verify live source workflow is green;
- freeze all upstream inputs before kickoff;
- persist full forecast distributions/intervals;
- preserve exact market timestamps and prices;
- preserve role/workload/news provenance;
- append immutable receipts;
- do not overwrite originals.

After the games finalize, run the same preregistered evaluator without changing thresholds or definitions.

## 6. Promotion rule

No Props successor should be promoted because it improves Week 2 retrospectively.

Promotion evidence must come from future untouched prospective weeks and should include:

- projection MAE/RMSE by family;
- proper probability scores and calibration;
- paired model-vs-market differences with game-clustered uncertainty;
- stability across multiple weeks/games;
- genuine original `MODEL EDGE` samples if betting performance is to be discussed.

Until that evidence exists, Props remains research/challenger status.

## 7. Repository hygiene

At this handoff, the intended active Props PRs are:

- **#458** — canonical current-main prospective evaluation / scientific record
- **#459** — live post-kickoff clean no-op lifecycle fix

Historical experimental PRs were intentionally closed or superseded so new chats should not revive them by default.

Separate Sunday Signal editorial recovery work is tracked independently and must not be allowed to delay the Props research lanes.
