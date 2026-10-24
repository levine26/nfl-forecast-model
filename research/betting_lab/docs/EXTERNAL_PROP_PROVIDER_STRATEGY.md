# External touchdown and yardage-provider integration — separate from game-market history

## Decision

No new TD or player-yardage historical validation in the Sunday sprint. Use an authorized **provider comparison/aggregation interface** instead; do not assume a public research methodology implies accessible provider forecasts or permission to import paid/proprietary intellectual property.

## Verified candidates (2026-10-10 research)

| Provider | Evidence & role | Initial comparison prior | Activation |
|---|---|---:|---|
| [CHZN1 nfl-anytime-td-model](https://github.com/CHZN1/nfl-anytime-td-model) | Open MIT code, 2021–23 training / 2024 selection / 2025 untouched test; ROC-AUC ~.688 RF. Strongest inspectable NFL-specific TD model of candidates. AUC is not betting ROI/calibration. | 3.5/5 | Require execution/reproduction, source/authorship, actual timestamped player predictions |
| [JMutammara/NFL](https://github.com/JMutammara/NFL) | Open two-stage NFL game + player model (heteroskedastic NN / LightGBM and Poisson TD). Useful complementary yardage framework; outcomes not independently reproduced. | 2.5/5 | Reproduce code/validate inputs and publication timestamps |
| [Custom Venom methodology](https://customvenom.com/methodology) | Public explanation of volume, efficiency, context, and projected full box scores + ranges. **Not verified as the user's “Jake Venom”; do not equate their identity.** No qualified numerical paid forecast API or reproducible win-rate. | 2.0/5 | User-supplied/licensed numeric projection feed and disclosure; otherwise research only |
| [GameDay Analytics NFL props methodology](https://nfl.gamedayanalytics.net/props/methodology) | Transparent market-specific projection and grading plan; independent model access/actual performance unverified. | 2.5/5 | Licensed player distributions, comparable full slate coverage, audit |
| StartWho / Firecrawl Alexandria | Market and prop quote consensus **not independent football model**; timestamp and usage permissions must be qualified separately. | 0/5 model weight | Market reference only, never an independent vote |

**Weights are provisional *engineering comparison priors*, not learned optimal ensemble coefficients.** Even real provider scores are descriptive comparison only, not betting-eligible. Weights normalize across **actual received, authorized, independent, pregame** model forecasts for the *same* game/player/market/line. Missing providers are excluded, never guessed to agree. Market consensus remains a separate anchoring and expected-value comparator, never an independent vote.

Run `python -m betlab.cli prop-providers` to inspect the registry; `python -m betlab.cli external-prop-consensus --input /private/authorized_provider_forecasts.json --out /private/consensus.json` only works with real source-specific historical/weekly external predictions supplied with authorized-use and capture evidence. No unauthorized scraping, subscription bypass, or invented access. Provisional outputs are tagged `UNVALIDATED_PROVIDER_CONSENSUS_NOT_BETTING_ELIGIBLE`.

## Prop recommendations for Sunday

- Do not call a sourced odds line an independent model projection.
- Do not run new TD/yardage historical model searches tonight.
- Only generate prop candidate comparisons once comparable real vendor forecasts (and timestamp-qualified sportsbook quotes for pricing) exist.
- If only one qualified model is available, show a single-source probability, never a “multi-model consensus.”

## Future bridge (after Sunday)

Validate calibration on *prospectively saved* player market predictions against sportsbook no-vig and closing movements. Learn ensemble weights only using previous periods' frozen predictions with strictly chronological cross-validation. Remove providers exhibiting market double counting or unqualified quote timestamps.