# LevLine Post-Week-4 Phase 3 — Frozen A/B/C Historical Results

**Run:** 2026-10-07 (research-only GitHub Actions; branch `research/post-week4-phase3-execution-20261007`)  
**Preregistration:** [PR #627](https://github.com/levine26/nfl-forecast-model/pull/627), committed at `b13fd61e4092db1aef11983df0fbf81e70f3f41e` **before results**, merged on `main` at `5e45a01a526ce264dd0e7fe95fe95c6a6cf3ceee`.  
**Execution PR:** #628, research-only.  
**Single authoritative roadmap:** [../LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md](../LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md).  
**Frozen official production:** `F-ST-01-FROZEN-2026` — **unchanged**.  
**Scientific status:** A = REJECT, B = REJECT, C = INCONCLUSIVE. **Nothing promoted.**

## Exact paired 2022–2025 benchmark and source controls

The immutable recovered F-ST component OOF was hash/sequence/identity checked (2,127 rows, 2018–2025); its frozen training frame was separately verified (1,615 rows, 2020–2025). The independently existing season-forward `build_chronological_logit_stack` reconstructed F-ST on **1,087** identical, uniquely keyed 2022–2025 games. Correct = **741**; Brier = **0.2106533484**; log loss = **0.6087126266**. By season: 2022 **182/271**, 2023 **185/272**, 2024 **195/272**, 2025 **179/272**. These per-season reference counts exactly agree with the pre-existing component-resolved audit `research/levline4_component_resolved_upset_audit_v1.json`; frozen **740/1087 final-coefficient reconstruction is deliberately a different comparator**.

For B/C the same execution additionally built historical 2012–2025 REG EPA, Elo, margin and prior-game features using `nflreadpy`/nflverse. It **verified all 1,615** official frozen training game IDs, seasons and binary targets against the rebuilt football frame, with no duplicate game IDs. The model received no completed 2026 outcome, no closing reconstruction, no Alexandria, no source-final injury state and no target-season label during its fit. Residual standardizers and margins are trained on preceding seasons; margin conversion scale uses preceding-season OOF residuals only. The source pipeline remains retrospective historical football data rather than a complete timestamped *publication* archive, so these are historical challenger results, **not** independent live PIT verification of individual raw feed revisions.

### Primary paired comparison

| Candidate | Correct / 1,087 | Accuracy | Change vs chronological F-ST | Switches vs F-ST (candidate only / F-ST only) | Week-block 95% CI for accuracy change | Research decision |
|---|---:|---:|---:|---:|---:|---|
| Frozen F-ST | 741 | 68.17% | — | — | — | INCUMBENT |
| **A — MKT-COMP-RESIDUAL-V1** | **730** | **67.16%** | **−1.012 pp (−11 wins)** | 59 (24 / 35), 40.68% switch win | [−2.317, +0.368] pp | **REJECT** |
| **B — MARGIN-RESIDUAL-WIN-V1** | **737** | **67.80%** | **−0.368 pp (−4 wins)** | 8 (2 / 6), 25% switch win | [−0.910, +0.093] pp | **REJECT** |
| **C — EARLY-STATE-SHRINKAGE-V1** | **749** | **68.91%** | **+0.736 pp (+8 wins)** | 52 (30 / 22), 57.69% switch win | [−0.362, +1.832] pp | **INCONCLUSIVE** |

Bootstrap is the preregistered 2,000-resample season-week block design (seed 26). The 95% intervals include **no improvement** for every candidate. Candidate C has the best **point estimate**, not statistically established superiority.

### By-season changes in correct winners relative to F-ST

| Candidate | 2022 | 2023 | 2024 | 2025 | Total |
|---|---:|---:|---:|---:|---:|
| A | −2 | −4 | −2 | −3 | −11 |
| B | −2 | −1 | −2 | +1 | −4 |
| C | **+6** | **−1** | **+3** | **0** | **+8** |

A lost ground in **every** season. B lost three of four and its margin-only diagnostic was **697/1087**, below the market/F-ST. C gained substantially in 2022, modestly in 2024, lost one in 2023, and was neutral in 2025. This is not a stable four-season improvement; excluding 2022 leaves only a +2 net gain.

### Secondary probability diagnostics

| Model | Brier (lower better) | Log loss (lower better) |
|---|---:|---:|
| F-ST | **0.210653** | **0.608713** |
| A | 0.211332 | 0.609832 |
| B | **0.210456** | **0.608357** |
| C | 0.211711 | 0.611331 |

B marginally improved proper scores but **lost four winner decisions**; under this **accuracy-primary** program that is not a winner-model advance. C gained eight winners but degraded both probability scores; this prevents claiming a broadly better probabilistic forecast. Calibration intercept/slope and individual game predictions are in the immutable `evidence/summary.json` and three keyed `candidate_*_oof.csv` files.

A four-component-only (no mean/std/range/boundary summaries) preregistered ablation happened to tie F-ST on winner accuracy **741/1087**, with Brier 0.210383 and log loss 0.608149. This is not the locked eight-feature primary A; it **cannot** be retroactively substituted as the chosen A model or promoted based on a same-population ablation.

### C mechanism and caution

C's research-only pregame historical state used the fixed preregistered season-to-season prior (60% previous team last-eight form, 40% preceding league mean), blended with current-season completed games as `n/(n+6)`. It included offense/defense state and pregame evidence-depth uncertainty, **not** a retrospective inferred current starter. The QB continuity channel was not qualified and was correctly omitted; C is therefore a narrow **team-state** test, not proof of a complete QB-aware structural-regime model.

C's preregistered slices: Weeks 1–4 **167/256 vs F-ST 167/256**, Weeks 1–6 **245/372 vs 243/372** (+2); Weeks 7+ **504/715 vs 498/715** (+6). **Most of C's +8 came after Week 6**, despite its early-season thesis; do not assert that the early-season transition mechanism has been isolated. Its market 50–55% diagnostic slice gained +10 wins (90 vs 80 on 146 games); that was **not a preregistered gating rule** and must not be turned into one without a new candidate ID and clean prospective test.

**Cross-document slice discrepancy requiring reconciliation:** the previous Phase 1–2 findings stated ~164 correct F-ST in Weeks 1–4 and ~241 in Weeks 1–6, whereas the new *game-keyed* reference reconstruction reports 167 and 243. The exact per-season incumbent counts, overall 741, source frozen F-ST hashes and method are consistent with the older component-resolved 2022–2025 audit. This discrepancy **does not** license a retroactive threshold fix or a switch to whichever slice favors C. Before an early-week-specific follow-up, reproduce both prior claims on exact game IDs and document the semantic/input difference, if any.

## Decisions / gate

1. **A REJECT.** A larger residual topology is not automatically informative. Do not rescue by choosing the four-component ablation or by re-fitting to 2026.
2. **B REJECT as a winner candidate.** Proper scores improved slightly but it lost 4 paired winners and 6 of its 8 change decisions. Retain margin work as a separate margin/ATS scientific domain, not as a winner override.
3. **C INCONCLUSIVE; eligible only for a newly frozen, independent prospective-shadow proposal.** Its +8 is driven by limited seasons, confidence interval crosses zero, probability quality worsens, and the purported W1–6 mechanism is weak. Do not silently adopt market-boundary conditional switches or a new shrinkage constant from historical slices.
4. **Frozen F-ST remains production.** Confidence/pick/official grading unchanged.
5. **D constrained gate, E market quality, F player events** are **not authorized as results-driven rescue combinations**. E/F PIT coverage remains its own qualification exercise; Alexandria remains separate, prospective only.

## Reproducibility and footprint

- Fixed code: `research/post_week4_phase3/run_candidates.py`; fixture tests: `test_run_candidates.py`.
- One-shot trigger: `research/post_week4_phase3/EXECUTE.md`; isolated workflow: `.github/workflows/research_post_week4_phase3.yml` (not the pregame/production pipeline).
- Successful historical execution: [Actions run 37694641650](https://github.com/levine26/nfl-forecast-model/actions/runs/37694641650).
- `evidence/summary.json`: training/source gates, complete paired scores, by-season/slices, leave-one-season-out, calibration, intervals.
- `evidence/candidate_A_oof.csv`, `candidate_B_oof.csv`, `candidate_C_oof.csv`: exact game keys and probabilities, plus candidate-specific diagnostics; `evidence/manifest.json` includes per-file SHA-256. No live production output was generated.
- Repository's independently scheduled research validation and firewall checks must pass on final PR head before research merge. A historical experiment is **not** a production authorization.

**Stopping point:** historical Phase 3 A/B/C execution and initial decision are COMPLETE. No fourth model, after-the-fact threshold, candidate combination or production promotion occurs here.
