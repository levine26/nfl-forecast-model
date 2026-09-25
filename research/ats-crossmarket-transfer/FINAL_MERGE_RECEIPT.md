# Final Merge Receipt — ATS Cross-Market Transfer V1

Status: **COMPLETE / CANONICAL HISTORICAL NEGATIVE RESULT**

This receipt closes `LEVLINE ATS CROSS-MARKET INFORMATION TRANSFER V1`. It records already-completed scientific evidence and the already-merged primary research package. It does not refit, retune, recalibrate, rescue, redesign, or promote any model.

## Canonical scientific execution

- scientific execution SHA: `d436ce88450d857b625add926206df4309ca7758`
- workflow run: `36079539800`
- artifact name: `ats-crossmarket-transfer-36079539800`
- artifact ID: `10841875970`
- artifact digest: `sha256:02e575b5f9dde7ac88211ac9d937d3cb023221b95945300262daba6543c9f5fa`
- outer seasons: `2022, 2023, 2024, 2025`
- exact common OOF N: `1087`
- completed-2026 outcomes used: `0`
- numerical/leakage preflight: `PASS`
- red-team audit: `PASS`
- production changed by scientific execution: `NO`

## Primary merge provenance

- primary research PR: `#583`
- exact validated PR head: `9fef48b3ccb3c8d76e059ecf5940371651d53a87`
- dedicated ATS cross-market exact-head validation: run `36080448266` — `SUCCESS`
- LevLine research firewall: run `36080448233` — `SUCCESS`
- LevLine repository-wide research validation: run `36080448090` — `SUCCESS`
- primary merge SHA: `f80a1445ec62ca55e114c6d38c550c926697cd20`
- merge verified on live `main`: `YES`

The primary PR diff was restricted to `research/ats-crossmarket-transfer/**` plus the two dedicated cross-market research workflow files. No protected production forecasting surface was modified.

## Canonical scientific result

Source winner signal on the exact 1,087 ATS rows:
- F-ST winner accuracy: `0.6816927322907084`
- market winner accuracy: `0.6761729530818767`
- F-ST minus market accuracy: `+0.5519779208831621` percentage points
- F-ST Brier: `0.21065334840485694`
- market Brier: `0.2101992905677052`
- F-ST log loss: `0.6087126266444343`
- market log loss: `0.6076472081285539`

Primary CPL log loss:
- `KMASS-MARKET`: `0.7696147398842025`
- `KMASS-MARKETML-IPROJ`: `0.7682207713551819`
- `ATS-XM-IPROJ-FST-V1`: `0.7691216273311867`
- `KMASS-MARKETML-MEANFIX`: `0.7686818974943873`
- `ATS-XM-IPROJ-MEANFIX-V1`: `0.7689795138306613`
- `ATS-XM-CPL-OFFSET-V1`: `0.7699924609494907`

Matched candidate-minus-null primary deltas:
- `ATS-XM-IPROJ-FST-V1`: `+0.000900855976004787`; 95% season+week block interval `[-0.0010097027463750285, +0.002749616685622483]`; favorable seasons `2/4`.
- `ATS-XM-IPROJ-MEANFIX-V1`: `+0.0002976163362740405`; 95% `[-0.001085668298200987, +0.0017166992897076603]`; favorable seasons `2/4`.
- `ATS-XM-CPL-OFFSET-V1`: `+0.0003777210652882833`; 95% `[-0.0010003390489456761, +0.0016853338554897047]`; favorable seasons `2/4`.

Holm-adjusted support is absent for all three F-ST candidates. Every primary F-ST candidate is therefore classified:

`NO_MATERIAL_IMPROVEMENT`

Implementation candidates: **NONE**.

## Central conclusion

The experiment supports cross-market **market-moneyline** coherence but does not support incremental F-ST ATS transfer. `KMASS-MARKETML-IPROJ` improves CPL log loss versus spread-only `KMASS-MARKET` by approximately `-0.0013939685290206`, but each F-ST transfer mechanism is worse than its strongest structurally matched market-only null on the aggregate primary point estimate, with paired uncertainty crossing zero and only two favorable outer seasons.

The chronology selector chose nonzero transfer weights in every outer season, including `alpha=1.25` for 2022, but the outer evidence did not validate those weights as beneficial. No greater-than-one ATS transfer claim is authorized.

Boundary-local diagnostics near `|spread| <= 2` are preserved as descriptive future-research evidence only. No post-hoc threshold, subset, selective betting rule, or production candidate was created from them.

## Final firewall

- `F-ST-01-FROZEN-2026`: unchanged
- Sunday Signal numerical forecasts: unchanged
- official ML probabilities: unchanged
- official fair spreads: unchanged
- ATS picks: unchanged
- grading/history: unchanged
- deployment: unchanged
- completed-2026 outcomes used for this historical experiment: `0`

The canonical human-readable results remain in `research/ats-crossmarket-transfer/RESULT_SUMMARY.md`; machine-readable results and exact OOF predictions remain under `research/ats-crossmarket-transfer/results/`.

**STOP. No production promotion is authorized by this program.**
