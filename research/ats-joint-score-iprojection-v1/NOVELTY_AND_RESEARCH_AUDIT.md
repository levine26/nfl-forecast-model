# ATS-JSIP-V1 — Novelty and Research Audit

**Status:** PRE-IMPLEMENTATION / PRE-RESULT  
**Candidate:** `ATS-JSIP-V1`

## Repository-history reconciliation

### Q2 is not the same mechanism

The authoritative Phase-2 receipt defines `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` as a one-dimensional discrete **margin** model. Its frozen support was `[-75,+75]`; it was structurally invalidated when folded endpoint mass exceeded the preregistered `0.001` threshold. It produced no accepted complete Q2 outer OOF, no accepted primary proper-score result, and no accepted Q2/Q3 blend.

The Q2 source confirms the mechanism: continuous normal/generalized-normal/Student-t margin families were discretized into integer margin cells and augmented by key-margin adjustments. Its endpoint tails were folded into `-75` and `+75`.

`ATS-JSIP-V1` therefore does not widen Q2's margin support or repeat its model. It starts in two-dimensional nonnegative final-score space `(H,A)`, uses adaptive non-folded numerical support, incorporates market total in team-score location, and derives the exact margin PMF only after the score-pair distribution has been built.

### Market Manifold V2 is not the same mechanism

The canonical V2 contract begins from `KMASS-MARKETML-IPROJ` and preserves its positive, negative, and tie masses while tilting relative probability **within margin-sign regions**. The canonical post-merge receipt rejects that smooth within-sign market-manifold mechanism on primary CPL log loss.

`ATS-JSIP-V1` performs no such residual shape tilt. Its possible difference from the null must arise from score-pair geometry and total-conditioned team-score structure before margin marginalization.

## Why joint score space is scientifically motivated

Published NFL exact-score research recognizes that American-football scoring is not well represented by a smooth generic score distribution because touchdowns, conversions, field goals, and safeties create distinctive discrete score patterns. Baker and McHale (International Journal of Forecasting, 2013, DOI `10.1016/j.ijforecast.2012.07.002`) modeled exact NFL scores with a scoring-process formulation and explicitly used bookmaker point spread and over/under information in out-of-sample forecasting.

That supports testing score-space structure directly rather than repeatedly perturbing a one-dimensional margin density.

## Why minimum-KL projection is scientifically motivated

Minimum-relative-entropy / entropy-pooling methods provide a general way to impose externally supplied probability constraints while minimizing KL divergence from a reference distribution. The relevant principle for this candidate is conservative updating: qualified market win information should alter only what is necessary to satisfy the win-probability constraint rather than granting the candidate unrestricted freedom to refit its entire score surface.

Relevant methodological references include:

- Attilio Meucci, David Ardia, Marcello Colasante, *Portfolio Construction and Systematic Trading with Factor Entropy Pooling* (Risk, 2014; SSRN 1742559).
- Attilio Meucci, *Mixing Probabilities, Priors and Kernels via Entropy Pooling* (2011; SSRN 1944303).

The application here is not a claim that finance and NFL scoring are substantively identical; the transferable object is the constrained minimum-KL inference method.

## Why V1 deliberately omits football-feature ML

The research question is narrower than 'build the most complicated ATS model.' Existing ATS research already contains feature-rich quantile and direct CPL challengers with negative incremental results. Adding EPA, Elo, QB state, injuries, or another residual learner to the same first score-space test would make attribution impossible if the challenger moved.

V1 therefore isolates this hypothesis:

> Does joint score geometry + market total + qualified ML constraint improve the exact ATS outcome distribution relative to the strongest one-dimensional market-constrained null?

A future football-feature extension is permissible only under a new candidate ID after V1 is closed.

## Data/provenance boundary

The authoritative ATS inventory establishes:

- historical spread line: qualified as an exact-horizon-opaque historical benchmark;
- historical spread-side juice: **not qualified**;
- historical total: available as a market field under the same opaque-horizon semantics;
- paired moneylines: qualified where both sides are populated for no-vig market-probability use;
- no missing price may be silently replaced by `-110`.

`ATS-JSIP-V1` inherits those semantics exactly. It does not claim close, T-120, consensus, or constituent-book provenance that the archive does not establish.

## Falsifiability

The candidate is useful even if it loses. A non-favorable CPL delta would be direct evidence that score-pair reconstruction and total-conditioned lattice structure, under this conservative V1 specification, do not add enough ATS distributional information beyond `KMASS-MARKETML-IPROJ` on the historical development sample.

That negative result would close another mechanism without contaminating production or authorizing post-hoc rescue.
