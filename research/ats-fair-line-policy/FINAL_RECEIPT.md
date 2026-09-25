# ATS Fair-Line Policy V1 — Final Phase Receipt

**Program:** `ATS-FAIR-LINE-POLICY-V1`  
**Status:** **COMPLETE**  
**Historical classification:** **NOT_ESTABLISHED**  
**Historical evaluation:** 2022–2025 expanding-season out-of-fold  
**Completed-2026 outcomes used:** **0**  
**Post-result threshold search:** **none**  
**Production winner/ATS separation:** **implemented independently of this result**

## 1. Question tested

This phase tested the exact decision logic observed on David Sasser's public NFL board and requested for LevLine:

> The outright winner and ATS value side are separate questions. Pick the ATS side according to the difference between the model's projected margin and the sportsbook spread, even when that side is the team projected to lose outright.

For LevLine, the frozen policy was:

- `edge_home = expected_margin - spread_line`;
- positive edge -> home ATS side;
- negative edge -> away ATS side;
- exact equality -> no edge;
- no tuned minimum edge threshold;
- no F-ST-winner agreement filter;
- no favorite/underdog rescue filter.

The ATS decision was therefore driven only by the independent LevLine expected-margin forecast versus the market spread.

## 2. Production implementation disposition

The semantic/decision-contract change is **not contingent on historical profitability**.

It was implemented and merged separately:

- backend/public-contract PR **#591**;
- backend merge: `2fb66c78459545d9981f8d38b5681f83c5dd29be`;
- contract version: `1.1`;
- outright winner remains the frozen F-ST win-probability output;
- ATS side is first-class and may disagree with the outright winner;
- first-class ATS fields include model margin, market margin, ATS edge, picked team, picked market spread, status, and winner/ATS agreement.

The Sunday Signal consumer surface was then implemented and merged separately:

- UI PR **#592**;
- UI merge: `110e86fe6f2d70761133b9f41f4364c9e30d0965`;
- responsive/browser validation passed;
- game pages display Outright Forecast, ATS Side, LevLine Model Line, Market Line, and an explicit `Winner / ATS split` explanation when applicable.

Therefore the architecture can represent a forecast such as **GB more likely to win / ATL +5.5 ATS value** whenever LevLine's independent expected margin is shorter than the sportsbook's GB margin.

## 3. Frozen historical execution

The preregistration was committed before target results were produced.

- preregistration SHA-256: `2326aea417d7c75774008e4d2bd2999ff96ac0ea102dc3a9e457d4957ee7ed39`;
- outer seasons: 2022, 2023, 2024, 2025;
- each outer target season used only prior seasons for model fitting;
- the production Core margin architecture was reproduced using ElasticNet, ExtraTrees, XGBoost and CatBoost with inverse validation-MAE weighting;
- 10,000 season-stratified week-block bootstrap draws;
- bootstrap seed: `20260925`.

Workflow evidence:

- workflow run: `36103926049`;
- job: `107972174355`;
- frozen execution head: `dea4fefc096502f1de062ac2fad69e4f781834b4`;
- workflow conclusion: **success**;
- artifact ID: `10850458558`;
- artifact name: `ats-fair-line-policy-v1-evidence`;
- artifact digest: `sha256:0d6ff09f27f876642c3d337d62e9b4a8298a77026f0f2e4f9152db153010b843`.

## 4. Primary result

Aggregate OOF ATS record:

- decisions: **1,087**;
- wins: **517**;
- losses: **541**;
- pushes: **29**;
- ex-push hit rate: **48.8658%**;
- exact 95% Clopper-Pearson interval: **45.8132% to 51.9247%**;
- reference -110 net units: **-78.10**;
- reference -110 ROI on risk: **-6.7108%**.

Week-block bootstrap:

- 95% interval: **45.8812% to 51.8096%**;
- `P(hit rate > 50%) = 0.2181`;
- `P(hit rate > 52.38095%) = 0.0099`.

The frozen gate therefore fails.

## 5. Season stability

| Season | W | L | P | Ex-push hit rate |
|---|---:|---:|---:|---:|
| 2022 | 133 | 128 | 10 | 50.9579% |
| 2023 | 115 | 143 | 14 | 44.5736% |
| 2024 | 130 | 138 | 4 | 48.5075% |
| 2025 | 139 | 132 | 1 | 51.2915% |

Only **2 of 4** seasons reached 50%.

## 6. Margin-model diagnosis

The independent LevLine margin model was not more accurate than the market spread center on the frozen OOF sample:

- LevLine margin MAE: **9.9617** points;
- market spread-center MAE: **9.4945** points;
- LevLine minus market MAE: **+0.4672** points, adverse to LevLine.

More importantly, the model-vs-market edge did not show useful directional association with the realized ATS residual:

- Pearson correlation: **-0.0293**, `p = 0.3343`;
- Spearman correlation: **-0.0255**, `p = 0.4015`.

This explains the primary result: the winner/ATS separation is mathematically coherent, but the current independent margin model is not accurate enough relative to the sportsbook spread to create an ATS edge merely by comparing the two lines.

## 7. Frozen selective diagnostics

These were preregistered diagnostic slices, not thresholds selected after inspection.

| Slice | Rows | Minimum absolute edge | W-L-P | Hit rate |
|---|---:|---:|---:|---:|
| Top 20% absolute edge | 218 | 3.9592 | 103-112-3 | 47.9070% |
| Top 10% absolute edge | 109 | 5.3320 | 56-52-1 | 51.8519% |

Neither diagnostic supports rescuing the policy through an edge-size threshold.

## 8. Final scientific conclusion

**The decision architecture is retained; the current margin signal is rejected as a standalone ATS solution.**

The Sasser-style separation solves a real LevLine design defect: the model must be able to say one team is more likely to win while the other side offers ATS value at the posted number. That logic is now implemented end-to-end and remains correct regardless of this historical result.

However, `ATS-FAIR-LINE-POLICY-V1` does **not** establish that LevLine's current independent expected-margin forecast can beat the spread market. On the frozen 2022–2025 development sample it underperformed both 50% directional accuracy and the reference -110 break-even rate, had worse margin MAE than the market, and showed essentially zero edge-to-residual association.

The next ATS research program therefore should **not** undo the winner/ATS separation. It should improve the fair-line estimator itself: explicitly train a chronology-safe model to estimate the true scoring margin / market residual with the sportsbook spread treated as a strong prior or offset, and validate whether the resulting model-vs-market residual contains stable information. That successor must be preregistered as a new experiment rather than created by post-hoc modification of this failed policy.

## 9. Phase closeout

- Backend decision contract: **IMPLEMENTED**.
- Sunday Signal ATS split UI: **IMPLEMENTED**.
- Frozen historical audit: **COMPLETE**.
- 2026 outcome firewall: **PASS**.
- Post-hoc threshold tuning: **NONE**.
- Historical classification: **NOT_ESTABLISHED**.
- Phase status: **CLOSED**.
