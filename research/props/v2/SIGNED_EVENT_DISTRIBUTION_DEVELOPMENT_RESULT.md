# LevLine Props 2.0 — Signed Event-Yard Distribution Development Result

Status: **RETROSPECTIVE COMPONENT ISOLATION — POSITIVE MECHANISM RESULT, NOT PREGAME PROP EVIDENCE**  
Workflow: `35383358262`  
Artifact: `10562609890`  
Contract: `levline-props-v2-signed-event-distribution-v0.1.0`  
Production promotion authorized: **NO**

## Frozen question

Does replacing the current nonnegative Gamma event-yard model with a signed empirical event-yard
distribution improve conditional rushing/receiving yardage distribution quality?

This study deliberately conditions on the **actual event count** for each player-game in order to
isolate yardage-per-event distribution shape from opportunity-count error.

Because actual event count is postgame information, this is **not a pregame prop forecast**.

## Aggregate result

2023–2025:
- N: **19,038** player-game/event-type rows;
- unique games: **855**;
- Gamma CRPS: **8.22001**;
- signed empirical CRPS: **8.20688**;
- signed minus Gamma CRPS: **−0.01313**;
- game-clustered 95% interval: **−0.01908 to −0.00761**;
- Gamma 80% interval score: **53.74665**;
- signed 80% interval score: **53.65604**;
- Gamma 80% coverage: **78.82%**;
- signed 80% coverage: **78.13%**.

The signed distribution therefore produces a small but statistically stable proper-score improvement,
with slightly narrower/less complete interval coverage.

## By season

| Season | N | Gamma CRPS | Signed CRPS | Δ CRPS | Clustered 95% CI | Gamma cov. | Signed cov. |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 6,421 | 8.26091 | 8.24640 | −0.01451 | −0.02387 to −0.00557 | 78.52% | 77.56% |
| 2024 | 6,294 | 8.27664 | 8.26597 | −0.01067 | −0.02135 to −0.00011 | 78.82% | 78.03% |
| 2025 | 6,323 | 8.12211 | 8.10792 | −0.01419 | −0.02340 to −0.00478 | 79.11% | 78.81% |

The CRPS improvement is directionally consistent in every evaluation season.

## By event type

### Rushing

- N: **6,993**;
- Gamma CRPS: **7.77122**;
- signed CRPS: **7.74268**;
- Δ CRPS: **−0.02854**;
- clustered 95% interval: **−0.03869 to −0.01840**;
- Gamma 80% coverage: **75.72%**;
- signed 80% coverage: **77.45%**;
- historical negative-event rate: approximately **11.14%**.

The signed-support benefit is concentrated most clearly in rushing, where negative plays are common
and the Gamma baseline is structurally incapable of producing them.

### Receiving

- N: **12,045**;
- Gamma CRPS: **8.48057**;
- signed CRPS: **8.47637**;
- Δ CRPS: **−0.00419**;
- clustered 95% interval: **−0.01043 to +0.00230**;
- Gamma 80% coverage: **80.61%**;
- signed 80% coverage: **78.52%**;
- historical negative-event rate: approximately **2.95%**.

Receiving shows only a small, non-established CRPS improvement and worse interval coverage.

## Scientific disposition

**ADVANCE SIGNED EVENT SUPPORT AS A MECHANISM CANDIDATE, NOT AS A PROPS 2.0 PROMOTION.**

The aggregate proper-score gain is real enough to justify replacing the structurally impossible
nonnegative rushing-event support in a new pregame simulation experiment. The result is strongest
for rushing and does not establish the same benefit for receiving.

The next scientific step must remove the postgame conditioning by combining signed event outcomes
with a genuinely pregame opportunity-count distribution, then evaluate the resulting full pregame
prop distribution with CRPS, calibration, Fair-Line error and market-relative probability metrics.

No production forecast, F-ST model, Props V1 output, market threshold, or 2026 candidate is changed
by this result.
