# ATS Red-Team & Leakage Checklist

No Phase-2 historical candidate result is interpretable until every applicable item below is tested or explicitly fail-closed.

## A. Spread sign / grading

- [ ] Canonical `M=home-away`, home favorite `L<0`, `R=M+L` asserted in code.
- [ ] Synthetic home -3 / win by 7 => cover.
- [ ] Synthetic home -3 / win by 3 => push.
- [ ] Synthetic home -3 / win by 2 => loss.
- [ ] Synthetic home +3 / lose by 2 => cover.
- [ ] Away-side probabilities are exact cover/loss reversal with same push.
- [ ] Whole-number and half-point lines are distinguished.
- [ ] Half-point push probability equals exactly zero.

## B. Market identity / timing

- [ ] Historical schedule market rows retain opaque closing/late label.
- [ ] No closing/later line is used as opening/T-120/current-at-earlier-horizon.
- [ ] Spread side price belongs to the same line, side, book and timestamp.
- [ ] Home price is never applied to away side.
- [ ] Vig removal uses both prices when a no-vig probability is claimed.
- [ ] Missing spread juice is not filled with -110 except explicit `REFERENCE_MINUS110` sensitivity.
- [ ] Multi-book consensus uses same-horizon constituent quotes only.
- [ ] Stale book quote is not silently treated as fresh consensus evidence.
- [ ] Later market data do not define earlier book dispersion/consensus.

## C. Chronology

- [ ] Random K-fold absent.
- [ ] Outer target season fits only prior seasons.
- [ ] Inner target year fits only years before that inner target.
- [ ] Scaling/imputation fitted training-only.
- [ ] Same-row quantile/model fitting impossible.
- [ ] Target-season residual scale absent from its own forecast.
- [ ] Target-season key-number frequency absent from its own Q2 parameters.
- [ ] Target-season probability calibration absent.
- [ ] Q2 receives only chronology-clean Q1 median predictions.
- [ ] Blend weight selected only from earlier inner OOF rows.

## D. Feature leakage

- [ ] Current-game PBP/result never enters current pregame feature.
- [ ] Final historical QB starter ID is not used as T-minus state without proof.
- [ ] Postgame inactive/snap/workload state absent.
- [ ] Realized weather absent as pregame forecast.
- [ ] Later depth-chart/roster corrections absent.
- [ ] News without preserved publication timestamp absent.
- [ ] Any optional field has provenance and as-of semantics.

## E. Completed-2026 firewall

- [ ] No completed 2026 result used for architecture.
- [ ] No completed 2026 result used for feature selection.
- [ ] No completed 2026 result used for quantile/distribution/key-number choice.
- [ ] No completed 2026 result used for hyperparameters/calibration/blending.
- [ ] No completed 2026 result used for threshold/selective rule.
- [ ] No completed 2026 result used for rescue/survival.
- [ ] Any live 2026 inspection is source qualification only and outcome-blind.

## F. Distribution integrity

- [ ] Q2 PMF nonnegative.
- [ ] Q2 PMF sums to one within `1e-12`.
- [ ] Boundary tail-folding tested and boundary mass reported.
- [ ] Key-number adjustments estimated from training only.
- [ ] Key-number list exactly `{3,6,7,10,14}` by absolute margin.
- [ ] Fixed distance bands unchanged.
- [ ] Push probability equals PMF mass at `M=-L` for integer line.
- [ ] Alternate-line probabilities are monotone in line direction.
- [ ] Cover + push + loss = 1 within tolerance.

## G. Q3 integrity

- [ ] Pushes are neither dropped nor coded as losses in three-outcome evaluation.
- [ ] Push head fits whole-number spread rows only.
- [ ] Half-point `p_push=0` contract enforced.
- [ ] No class rebalancing distorts probability calibration.
- [ ] Combined hurdle probabilities sum to one.
- [ ] No post-hoc isotonic/Platt rescue.

## H. Model-search / threshold discipline

- [ ] Q1 alpha grid unchanged.
- [ ] Q2 family/shape/penalty grids unchanged.
- [ ] Q3 C grid unchanged.
- [ ] Q2/Q3 blend grid unchanged.
- [ ] No new learner family after target results.
- [ ] No post-result feature interaction.
- [ ] No threshold fishing.
- [ ] No selective-subset mining beyond all/positive-EV/top20/top10.
- [ ] No key-number bucket creation after results.
- [ ] ROI/hit rate not used to override failed proper-score evidence.

## I. Data integrity

- [ ] Duplicate `game_id` rows rejected or deterministically reconciled before scoring.
- [ ] Exact common-row counts reported for every comparison.
- [ ] Missing spread rows excluded from ATS evaluation.
- [ ] Missing optional fields follow frozen imputation/missingness policy.
- [ ] Push grading agrees with raw scores and quoted line.
- [ ] Ties in final score are represented correctly in margin PMF/win outputs.

## J. Adversarial result checks

Any unusually positive result triggers, before interpretation:

- [ ] exact-row sign re-grade from raw scores/line;
- [ ] duplicate/leakage re-audit;
- [ ] season/week concentration report;
- [ ] key-number concentration report;
- [ ] market timing/provenance recheck;
- [ ] sensitivity to removal of single season;
- [ ] comparison to M0/M1/M2 on exact common rows;
- [ ] proof that no specification changed after target performance was seen.

Failure of a firewall item quarantines the affected evidence. It does not authorize a silent fix followed by retaining the original performance claim.