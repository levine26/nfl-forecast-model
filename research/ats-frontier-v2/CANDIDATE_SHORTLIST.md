# CANDIDATE SHORTLIST

Phase-1 research is frozen to four genuinely distinct mechanism families. This is not a performance ranking; no new candidate performance was inspected.

| ID | Mechanism | Information novelty | PIT feasibility prior | Main risk | Planning prior |
|---|---|---|---|---|---|
| `FRONTIER-M1-DYNAMIC-MARKET-STATE` | latent fair state from multi-book line + juice + ML + total path | **High** | Medium–High if paid historical snapshots qualify | later market level already sufficient | Small proper-score lift is plausible on eligible/volatile games; broad large ATS gains would be suspicious |
| `FRONTIER-M2-PLAYER-STATE-DELTA` | expected lineup/QB value change minus market-implied change | **High** | Medium / uncertain historically | public PIT status history incomplete; market assimilates faster | Event-concentrated small lift plausible; durable broad edge unlikely without superior timing |
| `FRONTIER-M3-HIERARCHICAL-STATE` | dynamic latent offense/defense/QB/unit strength with uncertainty/regimes | Medium | High for PBP, medium for unit/player PIT | becomes elegant A0; market still better state estimator | Modest predictive/proper-score improvement over fixed windows plausible, market incrementality uncertain |
| `FRONTIER-M4-DISCRETE-MARGIN-V2` | tail-safe conditional integer PMF / push-key representation | Low information novelty; High representation novelty | High for core score data | better calibration without alpha | Proper-score/calibration lift plausible; ATS edge should not be assumed |

## Expected-lift discipline

No numeric ATS percentage is promised. Planning priors are intentionally conservative because thousands of independent decisions would be required to separate small true edge from normal NFL ATS noise. A future result implying sustained 58–60% ATS performance over a modest sample should trigger leakage/selection audit before celebration.

## Data priority

1. M1 market history — highest priority because data access determines whether the strongest new information hypothesis is testable.
2. M2 player/QB PIT — second priority and likely harder; historical injury source continuity is a known obstacle.
3. M3 chronology-safe PBP/team/unit state — largely available, but roster transition timing must be qualified.
4. M4 numerical/distribution data — easiest core data, but deliberately lower edge prior.

## Ideas rejected before implementation

- another generic XGBoost/LightGBM NFL game model;
- transformer/neural network without a uniquely high-dimensional PIT source;
- static injury-status features;
- raw opening-to-current line movement as a candidate by itself;
- favorite/underdog/key-number betting rules mined from historical ATS returns;
- matchup interaction feature tournament;
- standalone backdoor-cover/drive simulator;
- residual stack/ensemble of existing failed LevLine models;
- exact rerun/rescue of Q1, Q2 V1 or Q3.

## Freeze

Phase 2 may eliminate shortlist members for data infeasibility. It may not add a fifth candidate because of target performance, because Phase 2 cannot inspect target performance. A genuinely new external scientific discovery may be logged as future research, but altering the Phase-1 shortlist requires an explicit governance amendment before any results are seen.