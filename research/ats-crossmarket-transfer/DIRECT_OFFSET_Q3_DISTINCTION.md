# Why `ATS-XM-CPL-OFFSET-V1` Is Not Q3

Q3 attempted to learn incremental ATS cover probability from a broader set of generic market and football-state inputs. Its failure therefore addressed a comparatively high-dimensional question: whether a generic feature learner could discover stable cover information beyond the sportsbook.

`ATS-XM-CPL-OFFSET-V1` asks a materially narrower question. Its only non-market covariate is

`delta_FST = logit(p_FST) - logit(p_market)`,

where `p_FST` is reconstructed with the chronology-clean historical version of the already-demonstrated winner-probability stack and `p_market` is the exact archived historical market probability used by that stack. The ATS model contains no fitted intercept, no interactions, no generic football-state matrix, no team/QB/injury/weather variables, and no flexible nonlinear learner.

The model preserves the baseline KMASS structural push probability and applies only

`logit(c) = logit(c0) + beta * delta_FST`

to conditional non-push cover probability. `beta` is selected from the frozen small grid using prior seasons only. Therefore a nonzero out-of-sample result would specifically support cross-market transfer of the pre-existing F-ST winner residual; a zero-weight result would specifically reject that transfer mechanism without reopening Q3 or generic ATS feature learning.
