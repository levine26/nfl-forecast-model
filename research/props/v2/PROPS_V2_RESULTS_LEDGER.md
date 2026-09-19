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

All six primary season/mode jobs completed successfully; the repaired canonical aggregate is from workflow `35417823424`, artifact `10577640488`. The earlier workflow `35381482900` supplied the same primary evidence but its first aggregate job failed on artifact flattening. The first
aggregate job failed only because same-named artifact files were flattened; the immutable primary
artifacts were recovered directly and the workflow was corrected to retain per-artifact directories.

### Route-only V2

- paired N **5,659**, 230 unique games, 307 unique players;
- challenger accuracy **50.96%** vs V1 **51.03%**;
- gain **−0.07 pp**;
- game-clustered 95% interval for accuracy difference approximately **−0.31 to +0.16 pp**;
- Fair-Line MAE **19.291** vs V1 **19.229**;
- CRPS **13.8983** vs V1 **13.8461**;
- 80% interval score **89.793** vs V1 **89.290**.

### Full V2

- paired N **5,659**;
- challenger accuracy **51.12%** vs V1 **51.03%**;
- gain **+0.09 pp**;
- game-clustered 95% interval for accuracy difference approximately **−0.95 to +1.15 pp**;
- Fair-Line MAE **19.820** vs V1 **19.233**;
- CRPS **14.3212** vs V1 **13.8481**;
- 80% interval coverage **71.78%** vs V1 **73.00%**.

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

## Opponent defensive-efficiency residual — positive component isolation

Workflow `35418742120`, artifact `10576851625`.

Actual event count was held fixed, so this isolates the conditional efficiency mechanism and is not
a pregame prop forecast.

Receiving:
- N **11,492**, 816 games, 681 players;
- baseline conditional total-yard MAE **12.08785**;
- challenger MAE **11.89335**;
- improvement **−0.19450**;
- clustered 95% interval **−0.22350 to −0.16535**;
- improvement occurs in 2023, 2024 and 2025.

Rushing:
- N **6,690**, 816 games, 520 players;
- baseline conditional total-yard MAE **11.02170**;
- challenger MAE **10.89129**;
- improvement **−0.13041**;
- clustered 95% interval **−0.16407 to −0.09864**;
- improvement occurs in 2023, 2024 and 2025.

**Disposition:** ADVANCE both rushing and receiving opponent-defense residual mechanisms to a true
pregame simulator ablation. Do not report these component gains as Props accuracy. Permanent record:
`DEFENSIVE_EFFICIENCY_DEVELOPMENT_RESULT.md`.

## Team offensive TD count overdispersion — rejected

Workflow `35418843763`, artifact `10577161142`.

2023–2025 aggregate:
- N **1,632 team-games / 816 games**;
- Poisson CRPS **0.746728**;
- negative-binomial CRPS **0.746728**;
- Poisson log loss **1.710151**;
- negative-binomial log loss **1.710151**;
- 80% coverage **92.95%** for both.

The frozen method-of-moments overdispersion estimate was **alpha = 0.0** in 2023, 2024 and 2025.
The challenger therefore collapses exactly to Poisson, zero seasons improve and the gate fails.

**Disposition:** REJECT `P2-TD-COUNT-V01`. Do not force a nonzero dispersion floor or retune the
evaluated mechanism. Permanent record: `TEAM_TD_COUNT_DEVELOPMENT_RESULT.md`.

## Signed rushing true-pregame ablation — rejected

Primary artifacts: 2023 `10577330985`, 2024 `10577865798`, 2025 `10577735587`.

All three primary jobs preserved V1's sampled carries exactly and used no target-game carries or
target-game yards for fitting.

2023–2025 aggregate, N **982**, 230 games, 114 players:
- V1 CRPS **18.26669**;
- signed-rushing CRPS **18.30423**;
- challenger minus V1 **+0.03754**;
- game-clustered 95% interval **+0.01576 to +0.06120**;
- V1 Fair-Line MAE **24.91395**;
- challenger Fair-Line MAE **24.93737**;
- MAE difference **+0.02342**;
- V1 80% coverage **62.32%**;
- challenger coverage **63.14%**.

Season CRPS differences:
- 2023 **+0.08278**;
- 2024 **+0.02573**;
- 2025 **−0.03189** on only 75 rows.

**Disposition:** REJECT `P2-DIST-RUSH-PREGAME-V01`. The positive conditional event-support result
did not survive integration with the full pregame V1 opportunity distribution. Do not tune residual
pools or variance against these evaluated outcomes. Permanent record:
`SIGNED_RUSHING_PREGAME_DEVELOPMENT_RESULT.md`.

## Opponent defensive efficiency — true-pregame passes

PR #394 preserves V1 opportunity-count arrays and changes only the strictly lagged opponent-defense
efficiency adjustment to yards/event means.

### Rushing

- N **941**, 230 games, 112 players;
- V1 CRPS **18.19360**;
- challenger CRPS **17.93138**;
- improvement **−0.26222**;
- game-clustered 95% interval **−0.34455 to −0.17871**;
- V1 Fair-Line MAE **24.85228**;
- challenger MAE **24.56642**;
- improvement **−0.28587**;
- coverage **62.17% → 62.91%**;
- CRPS improves in **3/3 seasons**.

Directional accuracy is diagnostic only and slightly declines **48.51% → 48.09%**.

### Receiving

- N **1,864**, 230 games, 256 players;
- V1 CRPS **19.18091**;
- challenger CRPS **18.77232**;
- improvement **−0.40859**;
- game-clustered 95% interval **−0.50123 to −0.32632**;
- V1 Fair-Line MAE **26.87741**;
- challenger MAE **26.31626**;
- improvement **−0.56116**;
- coverage **71.51% → 71.78%**;
- CRPS improves in **2/3 seasons**.

Directional accuracy is diagnostic only and slightly declines **50.13% → 49.81%**.

**Disposition:** BOTH event-type mechanisms pass the frozen true-pregame gate and become eligible for
a future prospectively frozen shadow challenger. This is not evidence of improved hit rate or betting
edge, and no production promotion is authorized. Permanent record:
`DEFENSIVE_EFFICIENCY_PREGAME_RESULT.md`.

## Defensive-efficiency prospective coefficient freeze

PR #396 completed the final pre-2026 coefficient freeze for the true-pregame defensive-efficiency
candidate using football event data through **2025 only**.

Frozen rushing fit:
- standardized beta **0.10603753**;
- intercept **−0.12662088**;
- x mean **0.00796987**;
- x sd **0.35506207**;
- training rows **13,243**.

Frozen receiving fit:
- standardized beta **0.21008098**;
- intercept **−0.33430875**;
- x mean **−0.09374150**;
- x sd **0.63468582**;
- training rows **22,925**.

Fit population: **180,791** event rows / **36,168** component rows.

Firewall audit:
- completed 2026 outcomes used: **0**;
- prop outcomes used: **0**;
- sportsbook results used: **0**;
- production authorization: **false**.

**Disposition:** coefficients are eligible only for untouched prospective shadow once the validated
pregame mechanism PR is merged. They may not be changed because of 2026 performance.

## Opponent defensive efficiency — true-pregame gates passed

Canonical PR **#394**, primary workflow `35419926356`.

The ablation preserved every V1 sampled opportunity-count array, used opponent-defense state only
from weeks strictly before the target week, fit residual coefficients only through season S−1, and
regenerated only the relevant yards/event distribution.

### Rushing

2023–2025:
- N **941**, 230 games, 112 players;
- V1 CRPS **18.19360**;
- challenger CRPS **17.93138**;
- challenger minus V1 **−0.26222**;
- game-clustered 95% interval **−0.34455 to −0.17871**;
- V1 Fair-Line MAE **24.85228**;
- challenger MAE **24.56642**;
- MAE improvement **−0.28587**;
- MAE clustered interval **−0.41022 to −0.16561**;
- coverage improves **62.17% → 62.91%**;
- CRPS improves in **3/3** seasons.

Frozen rushing gate: **PASS 5/5**.

Directional diagnostic: **48.51% V1 → 48.09% challenger** (slightly worse).

### Receiving

2023–2025:
- N **1,864**, 230 games, 256 players;
- V1 CRPS **19.18091**;
- challenger CRPS **18.77232**;
- challenger minus V1 **−0.40859**;
- game-clustered 95% interval **−0.50123 to −0.32632**;
- V1 Fair-Line MAE **26.87741**;
- challenger MAE **26.31626**;
- MAE improvement **−0.56116**;
- MAE clustered interval **−0.68187 to −0.44671**;
- coverage improves **71.51% → 71.78%**;
- CRPS improves in **2/3** seasons.

Frozen receiving gate: **PASS 5/5**.

Directional diagnostic: **50.13% V1 → 49.81% challenger** (slightly worse).

**Disposition:** ADVANCE both defensive-efficiency residuals to **prospective shadow eligibility**.
This is a full pregame distribution/Fair-Line improvement, not a demonstrated directional hit-rate or
betting-edge improvement. No production promotion. Permanent record:
`DEFENSIVE_EFFICIENCY_PREGAME_RESULT.md`.

## Prospective market-anchor shadow

Clean firewall-compliant implementation: **PR #379**.
Frozen candidates:
- market-only no-vig probability;
- market + frozen pre-2026 V1 residual.

This is a calibration/market-anchor experiment and is distinct from the football-mechanism shadow.
No completed 2026 outcome may change the candidate. Grading is evaluation-only.

## Prospective football Shadow A

Primary candidate: **P2-SHADOW-A-DEFENSE**.

Capture listener: **PR #402 — merged to `main` and active**.
It replays the exact V1 live manifest, applies only the frozen rushing/receiving defensive-efficiency
residuals, preserves every V1 opportunity array, uses the exact #394 mechanism RNG identity, and
writes immutable pregame receipts off `main`.

Each receipt is designed to preserve:
- season/week and kickoff/forecast/market timestamps;
- source workflow/head/forecast/manifest hashes;
- V1 signal + quality state;
- market line and no-vig probability;
- V1 and Shadow A Fair Lines/probabilities;
- lossless empirical V1 and Shadow A yardage PMFs for future CRPS;
- frozen defense state and coefficients;
- explicit zero-outcome-read / no-production governance.

Prospective football Shadow A receipts accumulated so far: **0**.
No pre-listener live run may be backfilled as prospective.

Grading implementation: **PR #406 — merged to `main`, frozen before the first eligible receipt/outcome**.
The grader uses finalized outcomes only, requires positive offensive snaps, preserves sportsbook void
semantics, computes CRPS/MAE/Brier/log loss/fixed-80%-interval/directional metrics, and never
auto-authorizes promotion.

Secondary **Shadow B (defense + Dynamic Role V0.1 full)** is now implemented by **PR #405**, merged to `main` with a separate immutable listener and separate evidence branch. Shadow B receipts accumulated so far: **0**. It replays V1, reconstructs the captured V1 opportunity distributions before applying the exact Dynamic Role V0.1 full transform, then applies the exact #394 defensive-efficiency overlay. No outcome before Shadow B's own first immutable receipt may count toward its prospective sample.

Shadow B grading is frozen separately in **PR #409** before the first B receipt/outcome. Its primary comparison is B vs matched Shadow A; B vs V1 is supporting context only. Unmatched B receipts cannot enter the B-vs-A minimum-evidence threshold.

## Prospective market archive activation status

The capture implementation exists in **PR #381**, including frozen exact-timestamp archive and
T48H/T24H/T12H/T6H/T90M/T30M/near-close horizon selection.

PR #381 has now been merged to `main`, so the automatic `workflow_run` listener is active.
The persistent branch `research-data/props-v2-market-archive` still does **not** exist, which means
no qualifying post-merge live refresh has produced the first immutable capture yet.

**Disposition:** prospective market evidence collection is **activated but has zero captures so far**.
Do not grade CLV/movement or describe evidence as accumulated until the first successful live refresh
creates the persistent archive branch and manifest.

## Production conclusion

No Props 2.0 architecture is scientifically authorized for production at this point. V1 remains the
published Props model while research and prospective evidence continue.
