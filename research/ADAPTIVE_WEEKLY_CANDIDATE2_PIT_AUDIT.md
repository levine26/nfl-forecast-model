# Candidate 2 Point-in-Time Feature Audit

Status: **PRE-RESULT / RESEARCH ONLY**  
Candidate: `ADAPTIVE-REGIME-SHOCK-GATE-V1`  
Preregistration base: `99b255aae7fc36ad367561f613e3fcb3752ef528`

This audit classifies requested Candidate 2 feature families by whether their historical point-in-time state can be reconstructed without substituting later knowledge.

| Feature family | Candidate 2 status | Historical scope | Evidence / contract | V1 use |
|---|---|---|---|---|
| Frozen F-ST probability / pick | fully PIT valid for established benchmark | 2022–2025 | `challenger_outputs/fst/provenance/training_frame_keyed.csv`; chronology-clean season-forward reconstruction | **ALLOW** |
| Raw historical market probability already embedded in F-ST provenance | fully valid for the established paired benchmark | 2022–2025 | same keyed provenance frame | **ALLOW** as comparator / component input |
| PURE aggregate | fully valid for established benchmark | 2022–2025 | same keyed provenance frame | comparator/context only; no generic upset override |
| Individual base-model OOF probabilities (`logistic`, `extra_trees`, `xgboost`, `catboost`) | fully valid under registered season-forward OOF lineage | 2022–2025 | `challenger_outputs/fst/provenance/base_oof_keyed.csv`; component-resolved audit | **ALLOW** |
| Component dispersion / votes / component-vs-market disagreement | fully valid when derived from the OOF probabilities above | 2022–2025 | `levline4_component_resolved_upset_audit_v1.json` | **ALLOW** |
| QB1 identity / QB1 change at T-120 | fully PIT valid **for 2025 only** | 2025 | `DEPTH-STATE-01`; `depth_chart_state_contract_v1.json`; source field `dt` and latest snapshot <= T-120 | **ALLOW 2025** |
| Rank-1 offensive-line continuity / new identities at T-120 | fully PIT valid **for 2025 only** | 2025 | same depth-state contract | **ALLOW 2025** |
| Rank-1 offense/defense continuity | fully PIT valid **for 2025 only** | 2025 | same depth-state contract | available but **EXCLUDED V1** except OL |
| Final-practice status from qualified injury reconstruction | fully PIT valid **for 2025 only** under conservative report-day bound | 2025 | `availability/2025_reconstruction_qualification_v1.json`; 6,064/6,068 identity matches; matched chronology before T-120 | **ALLOW practice state only** |
| Final game-status designation | partially PIT valid / not authorized as historical feature | 2025 | reconstruction explicitly retains it only as diagnostic because later revisions may occur | **EXCLUDE** |
| Game-day inactive state | unavailable at T-120 historically under a uniform qualified contract | 2022–2025 | prospective inactive archive starts in 2026; T-120 reconstruction forbids later inactive substitution | **EXCLUDE** |
| Rich starter probability / backup probability | prospective-only | 2026+ | `expected_lineup_qb_capture_v1_contract.json` | **EXCLUDE historical V1** |
| Role-weighted player availability probability | prospective-only / not numerically authorized | 2026+ | expected-lineup/player-state contracts | **EXCLUDE** |
| Unified 2022–2024 injury / availability state | unavailable historically under equivalent qualified semantics | 2022–2024 | cross-season availability harmonization failed closed | **EXCLUDE** |
| Opener -> current / strict T-120 market movement | unavailable historically under exact equivalent multi-book PIT capture | 2022–2025 | historical F-ST market probability exists, but exact multi-book path does not | **EXCLUDE** |
| T-120 -> T-60/T-45/T-30 movement, breadth, reversal, same-book overlap | prospective-only | 2026+ | `levline4_upset_evidence_contract_v1.json`; strict PIT collector | **EXCLUDE historical V1** |
| Closing line | post-horizon relative to T-120 decision | 2022–2025 | later information by definition | **PROHIBITED** |
| Coaching / play-caller changes | partially observable from public history but no equivalent frozen PIT repository contract | 2022–2025 | no qualified timestamped historical contract found | **EXCLUDE V1** |
| Scheme-change labels | unavailable as governed historical feature | 2022–2025 | would require hindsight/editorial inference | **EXCLUDE** |
| Verified roster transactions | partial source infrastructure; historical active-membership semantics not qualified | older / mixed | transaction and membership ledgers preserve failures/limitations | **EXCLUDE V1** |
| Rest / short week / bye | fully derivable from schedule | 2022–2025 | schedule chronology | technically valid but **EXCLUDED V1** by preregistration |
| Travel / time-zone / unusual venue | derivable with additional venue/travel mapping, but not required by V1 | 2022–2025 potential | venue research exists; no Candidate 2 numerical rule preregistered | **EXCLUDE V1** |
| Weather | historical contract not established for Candidate 2 common sample | mixed | weather capture is research infrastructure | **EXCLUDE V1** |
| Opponent-adjusted / QB-aware prior-game state | chronology-safe research artifacts exist | 2018–2025 | challenger OOF files | **EXCLUDE V1** to avoid changing the registered component mechanism |
| Candidate 1 residual state / past forecast errors | chronology-safe but scientifically rejected mechanism | 2022–2025 | Candidate 1 receipt | **CONTROL ONLY** |
| Completed 2026 outcomes | outcome leakage for Candidate 2 design | 2026 | project firewall | **PROHIBITED** |

## Exact Candidate 2 V1 historical domain

Candidate 2 V1 is therefore limited to **2025** for the orthogonal regime-shock channel.

The candidate still scores every paired 2025 game for which frozen F-ST and the registered component-resolved challenger are reconstructable. Missing personnel evidence is not a row exclusion and is never imputed into a shock; it forces the candidate to preserve F-ST.

This choice avoids the invalid alternative of treating 2022–2024 present-day injury knowledge as if it were known at the historical T-120 lock.

## PIT invariants

1. No depth-chart snapshot with `dt > kickoff - 120 minutes`.
2. No game-day inactive, snap, participation, final starter, or later revision may backfill T-120.
3. Qualified 2025 practice status is used only with stable GSIS identity and only under the pre-existing conservative report-day chronology proof.
4. Missing, ambiguous, conflicting, or unresolved identity/state fails closed.
5. No 2026 completed outcome enters feature generation, threshold choice, grid choice, or candidate selection.
6. The component stack uses only seasons strictly earlier than its target season.
7. Candidate 2’s shock gate supplies **authorization**, not winner direction.

## Scientific consequence

The desired broad Candidate 2 theory cannot be honestly tested on all 1,087 games with the currently qualified repository evidence. The strongest defensible historical test is a 2025 paired falsification experiment using T-120 QB/OL/practice-state discontinuities. Strict market microstructure and richer starter/inactive state remain prospective channels for any later frozen challenger.
