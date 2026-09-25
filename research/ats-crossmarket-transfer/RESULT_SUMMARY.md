# ATS Cross-Market Transfer V1 — Canonical Result Summary

Status: **COMPLETE HISTORICAL EXPERIMENT — NO MATERIAL F-ST ATS IMPROVEMENT**

Canonical scientific execution:
- execution SHA: `d436ce88450d857b625add926206df4309ca7758`
- workflow run: `36079539800`
- artifact: `ats-crossmarket-transfer-36079539800` (`10841875970`)
- artifact digest: `sha256:02e575b5f9dde7ac88211ac9d937d3cb023221b95945300262daba6543c9f5fa`
- outer seasons: 2022–2025
- common OOF N: 1,087 (2022: 271; 2023: 272; 2024: 272; 2025: 272)
- completed-2026 outcomes used: 0
- production changed: false
- numerical/leakage preflight: PASS

## Direct answer

**No.** The frozen historical experiment does not show that LevLine/F-ST's market-relative winner-probability displacement improves ATS probabilities beyond the strongest structurally matched market-only comparator.

There is, however, a useful positive cross-market result: historical **market moneyline** information improves the sportsbook-spread-centered KMASS baseline. The additional F-ST displacement does not add incremental ATS value on top of that market-moneyline information under any of the three preregistered transfer mechanisms.

## Source winner signal on the exact candidate rows

| Metric | F-ST | Market ML | F-ST minus market |
|---|---:|---:|---:|
| Winner accuracy | 0.6816927323 | 0.6761729531 | +0.5519779209 pp |
| Brier | 0.2106533484 | 0.2101992906 | +0.0004540578 |
| Log loss | 0.6087126266 | 0.6076472081 | +0.0010654185 |

F-ST therefore wins six more straight-up games over the 1,087-game sample, but its overall probability quality is slightly worse than the archived market probability on both Brier and log loss. This distinction matters for a proper-score ATS transfer experiment.

Per-season winner accuracy (F-ST / market):
- 2022: 0.6715867159 / 0.6568265683
- 2023: 0.6801470588 / 0.6764705882
- 2024: 0.7169117647 / 0.7169117647
- 2025: 0.6580882353 / 0.6544117647

## Primary CPL log-loss results

Lower is better.

| Model | CPL log loss | Matched reference | Candidate minus matched reference |
|---|---:|---|---:|
| KMASS-MARKET | 0.7696147399 | — | — |
| KMASS-MARKETML-IPROJ | 0.7682207714 | KMASS-MARKET | -0.0013939685 |
| ATS-XM-IPROJ-FST-V1 | 0.7691216273 | KMASS-MARKETML-IPROJ | **+0.0009008560** |
| F-ST I-projection, fixed alpha=1 | 0.7687963602 | KMASS-MARKETML-IPROJ | **+0.0005755888** |
| KMASS-MARKETML-MEANFIX | 0.7686818975 | KMASS-MARKET | -0.0009328424 |
| ATS-XM-IPROJ-MEANFIX-V1 | 0.7689795138 | KMASS-MARKETML-MEANFIX | **+0.0002976163** |
| ATS-XM-CPL-OFFSET-V1 | 0.7699924609 | KMASS-MARKET | **+0.0003777211** |

The simple market-moneyline I-projection improves the spread-only KMASS CPL score by about 0.001394. But every F-ST candidate has an adverse positive delta versus its matched null.

## Paired uncertainty and multiplicity

10,000 deterministic season + NFL-week block bootstrap resamples, seed 20260924:

| Candidate vs matched null | Delta | 95% interval | P(delta < 0) | Favorable seasons | Holm-adjusted support |
|---|---:|---:|---:|---:|---|
| ATS-XM-IPROJ-FST-V1 | +0.0009008560 | [-0.0010097027, +0.0027496167] | 0.1749 | 2/4 | no; adjusted p=1.0 |
| ATS-XM-IPROJ-MEANFIX-V1 | +0.0002976163 | [-0.0010856683, +0.0017166993] | 0.3504 | 2/4 | no; adjusted p=1.0 |
| ATS-XM-CPL-OFFSET-V1 | +0.0003777211 | [-0.0010003390, +0.0016853339] | 0.2882 | 2/4 | no; adjusted p=1.0 |

Raw one-sided bootstrap p-values used for the Holm family are 0.8251, 0.6496, and 0.7118 respectively. None approaches the advancement standard.

Per-season candidate-minus-null CPL deltas:

| Season | F-ST I-proj | Mean-fix F-ST | CPL offset |
|---|---:|---:|---:|
| 2022 | +0.0019007562 | +0.0000741506 | +0.0014550066 |
| 2023 | -0.0009601407 | -0.0009249026 | -0.0007300587 |
| 2024 | +0.0033540500 | +0.0023796823 | +0.0017372089 |
| 2025 | -0.0006875655 | -0.0003392865 | -0.0009473119 |

The sign pattern is 2 favorable / 2 adverse seasons for every candidate.

## Chronology-selected transfer weights

All selection was prior-season-only, and every historical validation season was itself scored with a nuisance fit trained strictly before that validation season.

| Outer season | alpha | beta |
|---|---:|---:|
| 2022 | 1.25 | 0.50 |
| 2023 | 0.75 | 0.50 |
| 2024 | 1.00 | 0.50 |
| 2025 | 0.50 | 0.25 |

The inner procedure never selected zero. It selected alpha=1.25 for 2022, but that greater-than-one weight did **not** validate out of sample: the 2022 F-ST I-projection delta versus its market-ML null was +0.0019007562 (worse). Therefore this experiment provides no validated evidence for greater-than-one ATS transfer weight.

## Calibration and conditional cover probability

Calibration intercept / slope:
- KMASS-MARKET: +0.0146732140 / 0.4404979429
- KMASS-MARKETML-IPROJ: +0.0166760226 / 1.2176893169
- ATS-XM-IPROJ-FST-V1: +0.0766980132 / 0.9934060767
- KMASS-MARKETML-MEANFIX: +0.0184797722 / 0.5650280047
- ATS-XM-IPROJ-MEANFIX-V1: +0.0473547232 / 0.7159264957
- ATS-XM-CPL-OFFSET-V1: +0.0361156657 / 0.4766965111

The selected simple F-ST I-projection triggers the preregistered material-calibration-degradation flag versus its market-ML null because of intercept worsening. The mean-fix and direct-offset candidates pass that calibration gate but still fail the primary proper-score and uncertainty gates.

Conditional non-push cover Brier / log loss:
- KMASS-MARKET: 0.2502145096 / 0.6935766002
- KMASS-MARKETML-IPROJ: 0.2495868629 / 0.6923197097
- ATS-XM-IPROJ-FST-V1: 0.2499343071 / 0.6930156503
- fixed alpha=1 F-ST I-proj: 0.2497584766 / 0.6926632201
- KMASS-MARKETML-MEANFIX: 0.2499193588 / 0.6929867237
- ATS-XM-IPROJ-MEANFIX-V1: 0.2497574027 / 0.6926606970
- ATS-XM-CPL-OFFSET-V1: 0.2504040528 / 0.6939646746

## Full-PMF diagnostics

Integer-margin log score:
- KMASS-MARKET: 3.8529284698
- KMASS-MARKETML-IPROJ: 3.8494100735
- ATS-XM-IPROJ-FST-V1: 3.8509798952
- fixed alpha=1 F-ST I-proj: 3.8505972169
- KMASS-MARKETML-MEANFIX: 3.8576673412
- ATS-XM-IPROJ-MEANFIX-V1: 3.8594309529

Discrete RPS / CRPS-style diagnostic:
- KMASS-MARKET: 6.9138756909
- KMASS-MARKETML-IPROJ: 6.8839464770
- ATS-XM-IPROJ-FST-V1: 6.8951497378
- fixed alpha=1 F-ST I-proj: 6.8920483959
- KMASS-MARKETML-MEANFIX: 6.9113813172
- ATS-XM-IPROJ-MEANFIX-V1: 6.9148969103

Maximum omitted adaptive-support baseline tail mass was `3.3558301395e-16`; no tail was folded into endpoints.

Expected-margin MAE diagnostic:
- KMASS-MARKET: 9.5042057446
- KMASS-MARKETML-IPROJ: 9.5037096861
- ATS-XM-IPROJ-FST-V1: 9.5196921104
- fixed alpha=1 F-ST I-proj: 9.5156502140
- KMASS-MARKETML-MEANFIX: 9.5042057446
- ATS-XM-IPROJ-MEANFIX-V1: 9.5042057446

The mean-preserving solver therefore did what it was designed to do: it preserved the sportsbook-centered KMASS mean to numerical precision. That constraint still did not reveal incremental F-ST ATS information.

## ATS diagnostic

All models score the same 1,087 games, with 29 realized pushes and 1,058 decisive ATS outcomes.

| Model | W-L-P | Ex-push hit rate | Exact 95% interval |
|---|---:|---:|---:|
| KMASS-MARKET | 540-518-29 | 51.0397% | [47.9809%, 54.0927%] |
| KMASS-MARKETML-IPROJ | 548-510-29 | 51.7958% | [48.7363%, 54.8454%] |
| ATS-XM-IPROJ-FST-V1 | 546-512-29 | 51.6068% | [48.5474%, 54.6573%] |
| fixed alpha=1 F-ST I-proj | 547-511-29 | 51.7013% | [48.6418%, 54.7514%] |
| KMASS-MARKETML-MEANFIX | 535-523-29 | 50.5671% | [47.5092%, 53.6219%] |
| ATS-XM-IPROJ-MEANFIX-V1 | 547-511-29 | 51.7013% | [48.6418%, 54.7514%] |
| ATS-XM-CPL-OFFSET-V1 | 540-518-29 | 51.0397% | [47.9809%, 54.0927%] |

Matched-null side switches:
- F-ST I-proj vs market-ML I-proj: 302 switches; 146-148-8, 49.6599% ex-push.
- F-ST mean-fix vs market-ML mean-fix: 164 switches; 84-72-8, 53.8462% ex-push.
- CPL offset vs KMASS-MARKET: 81 switches; 38-38-5, 50.0000% ex-push.

The reference-minus-110 outputs are hypothetical sensitivity only, not realized historical ROI because actual historical spread-side prices are unavailable.

## Transfer diagnostics

Fixed spread buckets, candidate minus matched-null CPL delta (negative is favorable):

| Spread bucket | F-ST I-proj | Mean-fix F-ST | CPL offset |
|---|---:|---:|---:|
| |spread| <= 2 | -0.005368 | -0.004653 | -0.002996 |
| 2 < |spread| <= 3.5 | +0.001425 | +0.001849 | +0.000387 |
| 3.5 < |spread| <= 6.5 | +0.002036 | +0.000883 | +0.000916 |
| 6.5 < |spread| <= 7.5 | +0.005095 | -0.000620 | +0.004764 |
| |spread| > 7.5 | +0.000605 | +0.000360 | -0.000294 |

Key-number buckets:
- F-ST I-proj: near 3 `+0.001425`; near 7 `+0.004601`; other `-0.000645`.
- Mean-fix F-ST: near 3 `+0.001849`; near 7 `-0.000355`; other `-0.000725`.
- CPL offset: near 3 `+0.000387`; near 7 `+0.004340`; other `-0.000843`.

The descriptive pattern is boundary-local rather than uniform: all three mechanisms have favorable point estimates when `|spread| <= 2`, while transfer generally degrades as the market spread moves farther from the win/cover boundary. In the preregistered joint diagnostic, the `|delta_FST|` 0.10–0.20 / `|spread|<=2` cell (N=64) is notably favorable (`-0.009818`, `-0.008398`, `-0.005710` for the three mechanisms). This is diagnostic only. No subset, threshold, or promotion rule was created from these results.

Larger F-ST disagreement does not monotonically improve ATS transfer. In the largest `|delta_FST|` 0.20–0.40 bin, aggregate deltas are adverse for all three mechanisms: approximately `+0.009468`, `+0.004621`, and `+0.004608`.

## Robustness

The simple F-ST I-projection is not being rejected because of one isolated week: every leave-one-season pooled delta is adverse, and leave-one-week deltas range from approximately +0.000585 to +0.001168 with zero sign flips. The CPL offset is similarly adverse across leave-one-week deletions. The mean-fix result is less concentrated, but its overall point estimate is still adverse and its paired interval crosses zero.

## Final classification

- `ATS-XM-IPROJ-FST-V1`: **NO_MATERIAL_IMPROVEMENT**.
- `ATS-XM-IPROJ-MEANFIX-V1`: **NO_MATERIAL_IMPROVEMENT**.
- `ATS-XM-CPL-OFFSET-V1`: **NO_MATERIAL_IMPROVEMENT**.
- implementation candidates: **none**.

`ATS-XM-IPROJ-MEANFIX-V1` has the smallest adverse primary point estimate among the three F-ST candidates, so it is recorded as the best point estimate mechanism only. It is **not** an implementation winner and does not pass the advancement gate.

## Scientific interpretation

The experiment supports a narrower decomposition than originally hoped:

1. The sportsbook spread remains the frozen location anchor.
2. Cross-market **market moneyline** information contains useful distributional information beyond spread-only KMASS under the simple sign-mass projection.
3. F-ST's historical straight-up accuracy advantage does not translate into better ATS proper scores once the archived market moneyline is already imposed.
4. The most plausible explanation in this sample is that F-ST's extra correct winner classifications are too sparse / boundary-specific and are not accompanied by improved aggregate probability calibration relative to market ML. Injecting the full continuous F-ST logit displacement therefore adds noise outside the narrow win/cover boundary region.
5. This is a historical negative result for these frozen transfer mechanisms, not evidence that every possible cross-market football signal is useless.

No production ATS model, F-ST probability, Sunday Signal forecast, fair spread, pick, grading surface, or deployment path is changed by this result.
