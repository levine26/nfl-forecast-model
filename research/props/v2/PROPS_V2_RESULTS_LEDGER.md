# LevLine Props 2.0 — Results Ledger

Status: **CURRENT THROUGH 2026-09-18**

## Frozen V1 benchmark

2023–2025 regular seasons, Weeks 1–18, primary genuine Action Network OPEN population:
- directional accuracy: **51.02%** (2,888 / 5,660 decided non-push props);
- Fair-Line MAE from the frozen diagnosis: approximately **19.18** versus sportsbook OPEN line MAE
  approximately **15.93**.

## Global market-prior residual — development evidence

Rolling-origin 2024–2025:
- N **4,109**, 153 unique games;
- challenger **53.74%** vs frozen V1 **51.23%**;
- paired gain **+2.51 pp**;
- game-clustered 95% interval approximately **+0.14 to +4.91 pp**.

On the 3,002 price-informative rows:
- sportsbook price direction **55.13%**;
- challenger **55.06%**;
- challenger minus market **−0.07 pp**;
- clustered 95% interval approximately **−1.11 to +0.98 pp**.

Probability scores:
- V1 Brier **0.28600**;
- market Brier **0.24608**;
- challenger Brier **0.24621**;
- V1 log loss **0.83248**;
- market log loss **0.68514**;
- challenger log loss **0.68540**.

**Disposition:** market anchoring is a material architecture improvement over V1; V1 residual signal
beyond the sportsbook is not established.

## Generic NGS residual

Fixed-anchor matched comparison:
- NGS residual accuracy approximately **52.26%**;
- matched market+V1 residual approximately **52.23%**;
- difference approximately **+0.02 pp**;
- game-clustered interval spans materially negative to positive values.

**Disposition:** REJECT as established incremental residual signal.

## Generic FTN matchup residual

Fixed-anchor:
- FTN residual approximately **52.21%**;
- matched baseline approximately **52.23%**;
- difference approximately **−0.02 pp**.

2024 rolling comparison was also negative, and probability scores did not improve.

**Disposition:** REJECT generic FTN residual signal.

## Prop-family market calibration

Fixed anchor:
- family-specific **52.49%** vs pooled global residual **53.60%**;
- difference **−1.11 pp**, clustered 95% interval **−2.40 to +0.12 pp**;
- Brier **0.24737** family vs **0.24650** global.

Rolling-origin 2024–2025:
- family-specific **52.74%** vs pooled global **53.74%**;
- difference **−1.00 pp**, clustered 95% interval **−2.19 to +0.17 pp**;
- Brier **0.24672** family vs **0.24621** global.

**Disposition:** REJECT; preregistered gate failed. Permanent record is
`PROP_FAMILY_MARKET_RESIDUAL_DEVELOPMENT_RESULT.md`.

## Dynamic role v0.1 — complete primary evidence

All six frozen season/mode primary artifacts from workflow `35375788109` completed successfully.
The first aggregate job had a file-flattening defect; the aggregate below was independently
reconstructed from the six immutable primary artifacts and is preserved in
`DYNAMIC_ROLE_V01_DEVELOPMENT_RESULT.md`.

### Full role adjustment

- paired N **5,658**, 230 unique games, 307 unique players;
- challenger accuracy **51.47%** vs V1 **51.03%**;
- gain **+0.44 pp**;
- game-clustered 95% interval for accuracy difference approximately **−0.11 to +1.02 pp**;
- challenger Fair-Line MAE **19.107** vs V1 **19.230**;
- paired MAE improvement approximately **−0.124**;
- game-clustered 95% interval for challenger-minus-V1 MAE approximately **−0.200 to −0.044**;
- sportsbook OPEN line MAE on the paired rows **15.973**.

**Disposition:** PROMISING FOOTBALL-PROCESS COMPONENT, NOT PROMOTION EVIDENCE. The Fair-Line error
improvement is stable enough to motivate a new role-state candidate, but directional improvement is
not established and the sportsbook line remains materially better.

### Route-only adjustment

- paired N **5,658**;
- challenger accuracy **51.06%** vs V1 **51.03%**;
- gain **+0.04 pp**;
- Fair-Line MAE **19.268** vs V1 **19.228**;
- clustered MAE-difference interval approximately **+0.015 to +0.071**.

**Disposition:** REJECT route-only V0.1 as a standalone improvement.

Dynamic Role V2 is a new candidate rather than a rescue tune of V0.1. Its state-transition parameters
are estimated from historical participation trajectories only, season-forward, with no prop outcomes
in the state fit. Proper distribution scoring (empirical CRPS and interval score/coverage) was frozen
before V2 primary evaluation.

## Dynamic role V2 v0.2 — rejected

All six primary season/mode jobs from workflow `35381482900` completed successfully. The first
aggregate job failed only because same-named artifact files were flattened; the immutable primary
artifacts were recovered directly and the workflow was corrected to retain per-artifact directories.

### Route-only V2

- paired N **5,659**, 230 unique games, 307 unique players;
- challenger accuracy **50.96%** vs V1 **51.02%**;
- gain **−0.05 pp**;
- game-clustered 95% interval for accuracy difference approximately **−0.29 to +0.18 pp**;
- Fair-Line MAE **19.294** vs V1 **19.229**;
- CRPS **13.8988** vs V1 **13.8455**;
- 80% interval score **89.802** vs V1 **89.278**.

### Full V2

- paired N **5,659**;
- challenger accuracy **51.09%** vs V1 **51.03%**;
- gain **+0.05 pp**;
- game-clustered 95% interval for accuracy difference approximately **−0.98 to +1.10 pp**;
- Fair-Line MAE **19.819** vs V1 **19.232**;
- CRPS **14.3209** vs V1 **13.8481**;
- 80% interval coverage **71.80%** vs V1 **73.00%**.

**Disposition:** REJECT Dynamic Role V2 V0.2. The latent state-space specification does not improve
the football distribution and full mode materially degrades it. The favorable small 2025 full
directional point estimate is not a rescue criterion. Permanent record:
`DYNAMIC_ROLE_V2_DEVELOPMENT_RESULT.md`.

## Signed event-yard distribution — positive component isolation

Workflow `35383358262`, artifact `10562609890`.

This experiment conditions on the realized event count for each player-game and therefore isolates
yardage-per-event distribution quality. It is **not** a pregame prop forecast.

2023–2025 aggregate:
- N **19,038**, 855 unique games;
- Gamma CRPS **8.22001**;
- signed empirical CRPS **8.20688**;
- signed minus Gamma **−0.01313**;
- game-clustered 95% interval **−0.01908 to −0.00761**;
- Gamma 80% coverage **78.82%**;
- signed 80% coverage **78.13%**.

Rushing carries most of the benefit:
- N **6,993**;
- CRPS improvement **−0.02854**;
- clustered interval **−0.03869 to −0.01840**;
- coverage improves **75.72% → 77.45%**;
- historical negative-event rate approximately **11.14%**.

Receiving is weaker:
- N **12,045**;
- CRPS improvement **−0.00419**;
- clustered interval **−0.01043 to +0.00230**;
- coverage declines **80.61% → 78.52%**.

**Disposition:** ADVANCE signed event support as a new pregame mechanism candidate, especially for
rushing. Do not treat this as prop accuracy or production evidence until event count is also
generated exclusively from pregame information. Permanent record:
`SIGNED_EVENT_DISTRIBUTION_DEVELOPMENT_RESULT.md`.

## Availability / workload mixture — retrospective source blocker

The preregistered Q/D four-state workload study reached no scientific model result because the
historical source cannot support a legal season-forward train/test chronology.

Source-qualified example counts:
- 2023: **0** prior training, **0** target examples;
- 2024: **0** prior training, **0** target examples;
- 2025: **0** prior training, **318** target examples.

Eligible evaluation seasons: **0**.

**Disposition:** STOP retrospective evaluation. Do not fit and evaluate on the same 2025 season,
infer historical injury state from final participation, or weaken the chronology gate. Continue only
as prospective timestamped injury/practice/status plus workload collection. Permanent record:
`AVAILABILITY_WORKLOAD_DATA_COVERAGE_RESULT.md`.

This is a data-coverage result, not evidence for or against the workload-mixture hypothesis.

## Game-environment residual — rejected

Workflow `35417908900`, artifact `10576338704`.

2023–2025, N **1,422** team-game rows / **711** games:
- baseline team-play MAE **6.87917**;
- challenger team-play MAE **6.91492**;
- challenger minus baseline **+0.03574 plays**;
- game-clustered 95% interval **+0.01396 to +0.05730**;
- baseline dropback-rate MAE **0.082411**;
- challenger dropback-rate MAE **0.082700**;
- dropback delta **+0.000289**, interval **−0.000436 to +0.001018**.

Team-play MAE worsened in **2023, 2024 and 2025**.

**Disposition:** REJECT `P2-GAME-ENV-V01`. Do not retune the evaluated formulation. Permanent
record: `GAME_ENVIRONMENT_DEVELOPMENT_RESULT.md`.

## Prospective shadow

Clean firewall-compliant implementation: **PR #379**.
Frozen candidates:
- market-only no-vig probability;
- market + frozen pre-2026 V1 residual.

No completed 2026 outcome may change the candidate. Grading is evaluation-only.

## Production conclusion

No Props 2.0 architecture is scientifically authorized for production at this point. V1 remains the
published Props model while research and prospective evidence continue.
