# LevLine Adaptive Weekly Learning — Candidate 2 Final Finding

Status: **historical Candidate 2 complete / INCONCLUSIVE / no production change**  
Candidate: `ADAPTIVE-REGIME-SHOCK-GATE-V1`  
Canonical execution SHA: `3d47141ed8584e989702d1982e4e1dc60d8248a2`  
Workflow run: `35749549009`  
Artifact: `10705320611`  
Artifact SHA256: `fc647c321190cebcda814a88a8159b7342894951aa7e80e07585928a5b4cb771`  
Full receipt: `research/ADAPTIVE_WEEKLY_CANDIDATE2_FINAL_RECEIPT.json`

The earlier pre-hardening Candidate 2 artifact is superseded as the final receipt. The canonical run above rebuilt the qualified 2025 practice-state archive, consumed only rows passing the historical PIT contract, ran the final Lane D/E tests, and reproduced the same primary winner result.

## Executive conclusion

Candidate 2 produced a **positive but scientifically inconclusive** 2025 historical point estimate.

On the exact 272-game 2025 paired sample:

- frozen F-ST: **179 / 272 = 65.8088%**;
- Candidate 2: **180 / 272 = 66.1765%**;
- delta: **+1 winner / +0.3676 percentage points**;
- Brier: **0.2114047 vs 0.2115784** (delta **-0.0001737**);
- log loss: **0.6072719 vs 0.6076199** (delta **-0.0003480**);
- winner switches: **1 / 272 = 0.3676%**;
- Candidate-2-only correct: **1**;
- F-ST-only correct: **0**;
- switch win rate: **100% (1/1)**.

The one authorized switch was `2025_12_ATL_NO`. F-ST was barely on New Orleans (home probability 0.509392), the independently reconstructed component challenger favored Atlanta (home probability 0.460679), and the preregistered orthogonal signal was a QB1 identity change. Atlanta won. OL churn and QB-practice state did not contribute to the switch.

That is directionally consistent with the Candidate 2 theory. It is **not enough evidence to establish a general edge**.

## Why the disposition is INCONCLUSIVE

The positive point estimate fails the evidentiary-strength test for promotion:

- exact McNemar diagnostic: **p = 1.0**;
- paired week-block error-loss diagnostic: **p = 0.3173**;
- 10,000-draw week-block 95% accuracy-delta interval: **0.0000 to +1.1278 pp**;
- bootstrap probability of positive accuracy delta: **0.6521**;
- all positive net gain comes from **one game in one week**;
- leave out Week 12 and the uplift becomes **0.0000 pp**;
- remove the QB-change channel and the uplift becomes **0.0000 pp**;
- QB-change-only reproduces the full +0.3676 pp;
- OL-churn-only and QB-practice-only produce no primary winner gain;
- season stability cannot be estimated because qualified equivalent regime-state history is available only for 2025.

Candidate 2 is therefore not rejected as directionally wrong, but it has not earned a claim of reproducible incremental winner information.

## Preregistered robustness grid

The frozen robustness grid contained 18 cells:

- F-ST boundary: 0.05 / 0.075 / 0.10;
- OL new-rank-1 threshold: 1 / 2 / 3;
- QB practice shock: DNP only / DNP-or-limited.

Results:

- **12 / 18** cells retained the +1 winner / +0.3676 pp result;
- **6 / 18** were neutral at 0.0000 pp;
- **0 / 18** were negative;
- the primary V1 configuration ranked tied-best;
- every OL threshold of 2 or 3 produced the same single correct QB-change switch;
- lowering the OL threshold to 1 added a second switch, producing one win and one loss and erasing the net gain;
- adversarial audit: **threshold fragility = true**.

This is better than a sign reversal, but the result remains **event-concentrated** and **QB-channel dependent**.

## Same-sample controls

On the exact same 272 games:

| Model | Correct | Accuracy | Delta vs F-ST | Switches vs F-ST | Switch record |
|---|---:|---:|---:|---:|---:|
| Frozen F-ST | 179 | 65.8088% | — | 0 | — |
| Market | 178 | 65.4412% | -0.3676 pp | 9 | 4-5 |
| Candidate 1 residual state | 182 | 66.9118% | +1.1029 pp | 27 | 15-12 |
| Naive weekly refit | 179 | 65.8088% | 0.0000 pp | 2 | 1-1 |
| Component-resolved | 179 | 65.8088% | 0.0000 pp | 4 | 2-2 |
| Boundary + component, no shock | 179 | 65.8088% | 0.0000 pp | 4 | 2-2 |
| Candidate 2 | 180 | 66.1765% | **+0.3676 pp** | 1 | **1-0** |

The Candidate 1 row is an important warning: Candidate 1 looks good on 2025 alone (+3 winners) even though its full 2022-2025 result is strongly negative and it was correctly rejected. That is direct LevLine-specific evidence against over-interpreting Candidate 2's one-season +1 result.

## Point-in-time data conclusion

Candidate 2 did not force unavailable evidence onto the 1,087-game benchmark.

Canonical 2025 coverage:

- both-team T-120 depth state: **272/272 games**;
- QB-change evaluable: **256 games**;
- OL-change evaluable: **256 games**;
- qualified QB-practice join: **127 games**;
- strong regime shock: **51 games**;
- F-ST boundary games: **50 games**;
- F-ST/component winner disagreements: **4 games**;
- authorized Candidate 2 switches: **1 game**;
- future depth-snapshot violations: **0**;
- depth postgame snaps used: **0**.

The canonical practice reconstruction independently cross-checked **6,068** nflverse rows against **6,068** official historical NFL report rows, achieved **99.9341%** stable-identity / fully-qualified coverage, **100%** practice-status agreement, and **100%** known-by-T120 rate among matched rows. Four unresolved player-week rows failed closed. Actual snaps, postgame participation, and completed 2026 outcomes used: **0**.

Historical T-60/T-45/T-30 market paths, final inactives learned after T-120, richer 2022-2024 availability, coaching/scheme text and hand-valued injury points remained excluded.

## External evidence interpretation

David Sasser's public board and public GitHub work reinforce a useful professional-practice principle: preserve model state, market state and time-stamped evidence separately rather than treating “market” as one opaque scalar. The public code inspected does not disclose a current chronology-safe weekly winner-retraining or regime-switch algorithm, so Candidate 2 did not copy one.

The external literature remains consistent with dynamic latent-state and structural-change mechanisms, especially the unusually high leverage of QB state. That literature motivates the mechanism; it does not validate the one historical switch.

## Answers to the Candidate 2 research questions

1. **What exact information produced the gain?**  
   A T-120 QB1 identity-change shock gated one near-boundary F-ST/component disagreement. No OL or QB-practice switch generated the gain.

2. **How often did Candidate 2 disagree with F-ST?**  
   1 / 272 games = 0.3676%.

3. **What percentage of switches were correct?**  
   1 / 1 = 100%, but this is statistically uninformative.

4. **Is the effect season-stable?**  
   Not estimable. Qualified equivalent regime-state evidence exists only for 2025.

5. **Did Brier/log loss improve?**  
   Yes, slightly: Brier by 0.0001737 and log loss by 0.0003480. Their week-block intervals reach zero.

6. **Is the result statistically distinguishable from noise?**  
   No. McNemar p=1.0, paired error-loss p=0.3173, and the week-block accuracy interval includes zero.

7. **Is the mechanism football-logically coherent?**  
   Yes. QB identity change is a plausible structural break, but the empirical support is one event.

8. **Is the gain reproducible?**  
   The exact historical computation is reproducible from the canonical execution SHA/workflow/artifact. Long-run generalization is not established.

9. **Suitable for prospective shadow testing?**  
   **No under Candidate 2 V1's preregistered rule.** V1 is positive and PIT-clean but entirely one-switch/one-week/QB-channel concentrated and threshold-fragile.

10. **Revised long-run accuracy estimate?**  
    The established frozen benchmark remains **68.1693%**. The current governance estimate for mechanisms actually evidenced so far is approximately **68.3%** central, with a practical near-term research range of roughly **68.2%-68.4%**. This is a research judgment, not a formal confidence interval. Current evidence does not support treating ~69% as an achieved or expected adaptive accuracy level.

## Scientific disposition

**INCONCLUSIVE**

Candidate 2 is more encouraging than Candidate 1 because it changed only one winner, that switch was correct, and probability quality also improved. But the evidence is too sparse and concentrated to establish incremental winner-selection information beyond frozen F-ST.

No production change is authorized. No prospective Candidate 2 shadow has been frozen. No prospective start week is assigned. Candidate 3 has not been started.
