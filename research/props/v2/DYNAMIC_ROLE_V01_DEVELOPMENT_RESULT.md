# LevLine Props 2.0 — Dynamic Role V0.1 Development Result

Status: **RETROSPECTIVE CHALLENGER DEVELOPMENT — NOT PROMOTION EVIDENCE**  
Source workflow run: `35375788109`  
Frozen contract: `levline-props-v2-dynamic-role-development-v0.1.0`

## Experiment

Two role ablations were frozen before the season-level evaluation:

- `route_only`: strictly lagged offensive snap participation changes route-role level only;
- `full`: the same route-role level plus recent-vs-long target and RB carry role trends.

The underlying V1 opportunity/efficiency/simulation framework remained paired and unchanged. Target
game snap counts were grading-only.

The six primary season artifacts all completed successfully. The original aggregate job failed only
because `merge-multiple: true` flattened same-named season files and overwrote one role mode. The
results below were reconstructed directly from the six immutable primary artifacts from the same
workflow run.

Primary artifact IDs:
- 2023 full: `10561450514`
- 2023 route_only: `10561151612`
- 2024 full: `10561596648`
- 2024 route_only: `10561511762`
- 2025 full: `10561250679`
- 2025 route_only: `10561210789`

The workflow on the challenger branch has since removed flattening so the canonical aggregate path
preserves both modes separately.

## Aggregate — full role adjustment

Paired decided props: **5,658**  
Unique games: **230**  
Unique players: **307**

- challenger accuracy: **51.47%** (2,912 / 5,658)
- paired V1 accuracy: **51.03%** (2,887 / 5,658)
- challenger minus V1: **+0.44 percentage points**
- game-clustered 95% interval for accuracy difference: approximately **−0.11 to +1.02 pp**
- challenger Fair-Line MAE: **19.107**
- paired V1 Fair-Line MAE: **19.230**
- challenger minus V1 MAE: approximately **−0.124**
- game-clustered 95% interval for challenger-minus-V1 MAE: approximately **−0.200 to −0.044**
- sportsbook OPEN line MAE on the paired rows: **15.973**

Thus the full role adjustment shows a modest but stable Fair-Line error improvement, while its
directional improvement is not statistically established.

### By season

| Season | N | Challenger acc. | V1 acc. | Δ accuracy | Challenger MAE | V1 MAE |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | 1,549 | 51.26% | 50.48% | +0.77 pp | 23.767 | 23.968 |
| 2024 | 3,696 | 51.16% | 50.81% | +0.35 pp | 17.419 | 17.515 |
| 2025* | 413 | 54.96% | 54.96% | 0.00 pp | 16.731 | 16.809 |

*The genuine-OPEN 2025 sample contains only 16 unique games and is not a full-season estimate.

### By prop family — descriptive only

| Prop | N | Challenger acc. | V1 acc. | Δ accuracy | Challenger MAE | V1 MAE |
|---|---:|---:|---:|---:|---:|---:|
| Passing TDs | 438 | 52.28% | 51.83% | +0.46 pp | 0.95 | 0.96 |
| Passing yards | 450 | 52.44% | 53.11% | −0.67 pp | 61.66 | 61.68 |
| Receiving yards | 1,943 | 50.95% | 50.44% | +0.51 pp | 26.63 | 26.85 |
| Receptions | 1,847 | 52.46% | 52.08% | +0.38 pp | 2.15 | 2.19 |
| Rushing yards | 980 | 49.80% | 48.88% | +0.92 pp | 24.72 | 24.91 |

These subgroup rows are diagnostics only. No family is selected or promoted from them.

## Aggregate — route-only adjustment

Paired decided props: **5,658**

- challenger accuracy: **51.06%**
- paired V1 accuracy: **51.03%**
- challenger minus V1: **+0.04 pp**
- game-clustered 95% interval: approximately **−0.18 to +0.25 pp**
- challenger Fair-Line MAE: **19.268**
- V1 Fair-Line MAE: **19.228**
- challenger minus V1 MAE: approximately **+0.041**
- game-clustered 95% interval for MAE difference: approximately **+0.015 to +0.071**

The route-only ablation slightly worsens Fair-Line MAE and does not establish directional gain.

## Scientific disposition

**FULL DYNAMIC ROLE V0.1: PROMISING FOOTBALL-PROCESS COMPONENT; NOT PRODUCTION-AUTHORIZED.**

The evidence supports continuing role modeling because the full adjustment improves Fair-Line MAE
consistently enough that the game-clustered interval for paired MAE improvement excludes zero.
However:

- the directional-accuracy interval crosses zero;
- the sportsbook OPEN line remains materially better on MAE;
- 2023–2025 are already-inspected retrospective development seasons;
- no result demonstrates incremental signal after the market is known.

The correct next step is a genuinely new role-state model with parameters estimated from role
trajectories rather than prop outcomes, followed by prospective validation. That is candidate
`P2-ROLE-V2`.

**ROUTE-ONLY V0.1: REJECT as a standalone improvement.** It worsens paired MAE and adds essentially
no directional value.

Neither result may be rescued or reframed through favorable retrospective subgroups.
