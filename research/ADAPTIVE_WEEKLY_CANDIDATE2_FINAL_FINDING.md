# LevLine Adaptive Weekly Learning — Candidate 2 Final Finding

Status: **historical Candidate 2 complete / INCONCLUSIVE / no production change**  
Candidate: `ADAPTIVE-REGIME-SHOCK-GATE-V1`  
Validated candidate code SHA: `f4a5ea26bc999819d4c79179c20b8f33fd77401f`  
Workflow run: `35747145825`  
Artifact: `10703836596`  
Artifact SHA256: `9039919437fc5b3fb48989e31b07fa592379d5fdc509e2cdabd3d9c3142654e5`  
Full receipt: `research/ADAPTIVE_WEEKLY_CANDIDATE2_FINAL_RECEIPT.json`

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

The one authorized switch was `2025_12_ATL_NO`. F-ST was barely on the home side (0.509392), the pre-existing component-resolved challenger was on the away side (0.460679 home probability), and the preregistered orthogonal shock was an away-team QB1 identity change. The switch was correct.

That result is directionally consistent with the Candidate 2 hypothesis: an abrupt QB state change can identify a case where frozen F-ST may be stale. It is **not enough evidence to establish a general edge**.

## Why the disposition is INCONCLUSIVE

The positive point estimate fails the evidentiary-strength test for promotion:

- exact McNemar diagnostic: **p = 1.0**;
- week-block bootstrap 95% accuracy-delta interval: **0.0000 to +1.1278 pp**;
- all positive net gain comes from **one game in one week**;
- leave out Week 12 and the Candidate 2 uplift becomes **0.0000 pp**;
- remove the QB-change channel and the uplift becomes **0.0000 pp**;
- QB-change-only reproduces the full +0.3676 pp;
- OL-churn-only and QB-practice-only produce zero switches under the primary specification;
- season stability cannot be estimated because qualified equivalent regime-state history is available only for 2025.

Therefore Candidate 2 is not rejected as directionally wrong, but it has not earned a claim of reproducible incremental winner information.

## Preregistered robustness grid

The frozen robustness grid contained 18 cells:

- F-ST boundary: 0.05 / 0.075 / 0.10;
- OL new-rank-1 threshold: 1 / 2 / 3;
- QB practice shock: DNP only / DNP-or-limited.

Results:

- **12 / 18** cells retained the +1 winner / +0.3676 pp result;
- **6 / 18** were neutral at 0.0000 pp;
- **0 / 18** were negative;
- every OL threshold of 2 or 3 produced the same single correct QB-change switch;
- lowering the OL threshold to 1 added a second switch, producing one win and one loss and erasing the net gain.

This is better than a threshold-fragile sign reversal, but the result remains **event-concentrated** and **QB-channel dependent**.

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

Validated 2025 coverage:

- both-team T-120 depth state: **272/272 games**;
- QB-change evaluable: **256 games**;
- OL-change evaluable: **256 games**;
- qualified QB practice join: **126 games**;
- strong regime shock: **51 games**;
- near-boundary component/F-ST disagreements: **4 games**;
- authorized Candidate 2 switches: **1 game**;
- future depth-snapshot violations: **0**;
- ambiguous QB-practice joins: **0**.

Historical T-60/T-45/T-30 market paths, final inactives learned after T-120, richer 2022-2024 availability, coaching/scheme text and hand-valued injury points remained excluded.

## Sasser / external evidence update

David Sasser's public 2026 CFB board exposes model projection alongside **Open** and **Current** market lines. His older public GitHub `davidsasser/BettingModel` code also explicitly collected timestamped, book-specific NFL moneyline/spread/total observations across multiple books. That is useful professional-practice evidence for preserving market identity and path rather than reducing "market" to one scalar.

The public GitHub code inspected is historical (2019/2020) and is **not** treated as the current 2026 Sasser model implementation. It does not reveal a current weekly retraining, injury-weighting or change-point algorithm.

External literature remains consistent with the mechanism, but does not prove it:

- Cattelan, Varin & Firth, dynamic Bradley-Terry sports ability: DOI `10.1111/j.1467-9876.2012.01046.x`;
- Macrì-Demartino, Egidi & Torelli (2026), sparse dynamic Bradley-Terry innovations that relax shrinkage around sudden changes: DOI `10.1186/s40537-026-01486-6`;
- Hoffer & Pincin (2019), NFL player point-spread values with quarterbacks dominating player value: DOI `10.1177/1527002519832060`;
- Miller & Rapach (2013), three sequential NFL betting-line states with increasing information content during the week: DOI `10.1016/j.jempfin.2013.07.002`;
- Krieger & Davis (2024), NFL line movement and market visibility: DOI `10.1007/s12197-023-09656-5`;
- Simon (2024), real-time sportsbook line sequences can overreact rather than improve monotonically: DOI `10.1287/mnsc.2022.00456`.

The main actionable external implication is **prospective strict-PIT multi-book market-shock research**, not retrospective substitution of closing lines.

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
   Yes, slightly. Brier improved by 0.0001737 and log loss by 0.0003480.

6. **Is the result statistically distinguishable from noise?**  
   No. McNemar p=1.0 and week-block bootstrap includes zero.

7. **Is the mechanism football-logically coherent?**  
   Yes. QB identity change is a plausible structural break and external NFL player-value evidence supports QB state as unusually high leverage. Empirically, however, the evidence is one event.

8. **Is the gain reproducible?**  
   The exact historical computation is reproducible from the recorded code SHA/workflow/artifact. The *generalization* of the gain is not established.

9. **Suitable for prospective shadow testing?**  
   **Not authorized from V1 evidence.** The preregistration required a positive, PIT-clean, coherent result that was not pathologically concentrated. V1 is positive and clean but entirely one-switch/one-week/QB-channel concentrated.

10. **Revised long-run accuracy estimate?**  
    The original ~68.8% adaptive central prior is no longer supported. The current evidence supports a central long-run estimate around **68.3%**, with roughly **68.2%-68.4%** the defensible near-term range for mechanisms actually evidenced so far. Larger gains remain possible only if genuinely orthogonal prospective market/player-state channels validate.

## Scientific disposition

**INCONCLUSIVE**

Candidate 2 is more encouraging than Candidate 1 because it changed only one winner, that switch was correct, and probability quality also improved. But the evidence is too sparse and concentrated to establish incremental winner-selection information beyond frozen F-ST.

No production change is authorized. No prospective Candidate 2 shadow has been frozen. Candidate 3 has not been started.
