# ATS-JSIP-GAUSSIAN-V1 — Design Rationale and Successor Selection Memo

**Status:** PRE-IMPLEMENTATION / PRE-TARGET-SCORING  
**Candidate:** `ATS-JSIP-GAUSSIAN-V1`  
**Production authorization:** NONE  
**Completed-2026 outcomes used:** 0

## 1. Why a successor is scientifically justified

`ATS-JSIP-V1` never reached historical target scoring. Its canonical null reproduced correctly, but the frozen Student-t support rule was internally infeasible: all 2,174 team-score axes across the 1,087 canonical target rows failed every legal `(df, scale)` pair at support 160, and no target candidate probability, proper score, ATS result, calibration statistic, bootstrap result, hit rate, or ROI was produced.

That means the joint-score hypothesis itself remains untested.

The next experiment should therefore resolve the numerical defect while changing as little of the scientific mechanism as possible. Introducing a feature-rich learner, new market microstructure inputs, score correlation, or a different ATS target at this point would destroy attribution.

## 2. Why the Gaussian kernel is the selected successor mechanism

The V1 defect was caused by polynomial Student-t tails interacting with an extremely strict `1e-12` omitted-tail requirement and a finite computational ceiling. A Gaussian location-scale kernel has exponentially decaying tails, making the same adaptive non-folded numerical strategy practical without weakening the tolerance.

The Gaussian is not being adopted because target-season ATS results preferred it; no V1 target results exist. It is selected prospectively because it removes the demonstrated support pathology while retaining:

- the same market-implied team-score locations;
- the same market total as a first-class input;
- the same football integer-score lattice correction;
- the same joint home/away score construction;
- the same qualified paired-moneyline minimum-KL sign projection;
- the same exact margin marginalization;
- the same primary null;
- the same CPL primary selector;
- the same chronological evaluation design.

This is the smallest architecture change that permits a clean test of the intended score-space hypothesis.

## 3. Literature support for score-space modeling

Baker and McHale, *Forecasting exact scores in National Football League games*, International Journal of Forecasting 29(1), 2013, DOI `10.1016/j.ijforecast.2012.07.002`, explicitly model NFL exact scores and emphasize that American-football scoring produces a non-standard integer distribution because touchdowns/conversions, field goals, and safeties create recurring score combinations. Their out-of-sample model also uses bookmaker point spread and over/under information.

That directly supports the core premise retained here: if the goal is to recover exact ATS boundary mass, it is scientifically reasonable to model home/away score space rather than endlessly perturbing a smooth one-dimensional margin density.

The same paper's literature review notes prior NFL work in which a normal approximation to margin behavior was usable. This does **not** imply that raw NFL team scores are Gaussian. `ATS-JSIP-GAUSSIAN-V1` explicitly corrects the smooth Gaussian structural kernel with an empirically estimated football score-cell multiplier before constructing the joint prior.

## 4. Why not simply widen the Student-t support

A pure support expansion would preserve V1's kernel but would retain the exact mechanism that caused the computational pathology. The V1 closeout showed only the **best** legal Student-t pair needed approximately 340–360 points of support to meet `1e-12`; heavier legal Student-t pairs can require substantially more because polynomial tails decay slowly.

A very large two-dimensional score grid would increase computation sharply and make the experiment's numerical behavior dominated by a tail assumption that is not itself the scientific target.

The Gaussian successor instead keeps the tail tolerance strict and makes the support approximation numerically subordinate to the actual research question.

## 5. Why not jump immediately to a maximum-entropy or richer joint model

A finite-lattice maximum-entropy / multi-constraint I-projection model is a scientifically interesting future candidate. Minimum-KL projections under linear constraints have a well-established exponential-family interpretation and can impose market-consistency conditions conservatively.

However, moving directly from V1 into a new base-measure family, simultaneous moment constraints, correlation structure, or score-pair interactions would answer a different question and confound the reason V1 failed.

The program should first test the original joint-score idea under a numerically feasible structural kernel. If `ATS-JSIP-GAUSSIAN-V1` is non-favorable, richer score-space models can then be justified as genuinely new hypotheses rather than rescue attempts.

## 6. Why not return to direct margin tilts

ATS Market Manifold V2 already tested a low-capacity within-sign margin-shape extension of `KMASS-MARKETML-IPROJ` and found no material improvement. The accepted result showed the stronger market-only null remained superior; after the first outer season, the chronology-clean selector collapsed later candidate weights to the null.

The successor therefore does not reopen:

- smooth moneyline-residual margin tilts;
- F-ST residual transfer;
- direct CPL learners;
- generic feature-rich ATS residual models;
- center replacement.

Its only intended new information channel remains total-conditioned score-pair geometry.

## 7. Why the scale grid is inherited unchanged

The frozen Gaussian scale grid is:

`{8, 10, 12, 14}`.

These values are inherited from the V1 structural scale grid rather than retuned after the support failure. Removing the `df` dimension is sufficient to isolate the tail-family change.

Selection remains prior-only and chronology-clean using observed-cell team-score log loss.

No target ATS result is allowed to determine the scale grid.

## 8. Why the support ceiling is 200

The candidate retains the strict omitted-tail requirement `<1e-12`, begins at `0..80`, and expands by 20.

The hard ceiling is prospectively set to 200 to provide a materially wider numerical safety margin than V1 while keeping the experiment computationally bounded. The implementation is not allowed to assume this is sufficient: before target scoring it must explicitly prove, for every canonical target input and **every legal Gaussian scale**, that both team axes satisfy the tail tolerance at or below 200.

Thus the new ceiling is not a silent approximation. It is a falsifiable pre-target invariant.

## 9. Expected mechanism of possible ATS improvement

The canonical null models the integer margin directly and already incorporates spread location, accepted scale/key-mass structure, and qualified moneyline sign mass.

The Gaussian joint-score challenger can only improve if the sportsbook total changes the shape of the implied **margin distribution around the ATS boundary** in a way the one-dimensional null does not capture.

For example, two games with the same spread but materially different totals can have different plausible home/away score combinations and different concentrations of exact integer margins after football score-lattice correction. The candidate tests whether that score-pair geometry improves calibrated Cover/Push/Loss probabilities.

This is a narrow, falsifiable mechanism. If primary CPL does not improve, the experiment closes that version of the hypothesis regardless of side-switch hit rate or reference ROI.

## 10. Advancement discipline

A favorable point estimate alone is insufficient.

The candidate must beat `KMASS-MARKETML-IPROJ` on aggregate paired CPL, satisfy the frozen 10,000-resample week-block uncertainty gate, avoid adverse seasonal concentration, pass calibration and robustness diagnostics, and pass all chronology/leakage/support/firewall invariants.

Even a successful historical result is only development evidence and can authorize at most a prospective shadow phase.
