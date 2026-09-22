# Adaptive Weekly Learning — Candidate 2 Evidence & Mechanism Review

Status: **Candidate 2 preregistered research / no production change**  
Candidate: `ADAPTIVE-REGIME-SHOCK-GATE-V1`  
Preregistration base: `99b255aae7fc36ad367561f613e3fcb3752ef528`

## Purpose

This review was completed after Candidate 2's feature family and primary thresholds were frozen. It is mechanism support and falsification context, not a source of post-result tuning.

## LevLine-specific prior evidence

1. **Frozen F-ST is difficult to improve by broad adaptation.** Candidate 1 residual-state learning lost 19 winners on 1,087 games and the weekly-refit negative control lost two. This rejects generic "learn harder from prior misses" as the Candidate 2 mechanism.
2. **Useful historical winner changes are sparse and boundary-local.** Frozen F-ST beat the raw market 20–14 on 34 disagreements, with no F-ST/market disagreement beyond roughly 54% market favorite probability.
3. **Component resolution retains potentially useful information.** The historical component-resolved L2 stack scored 744/1,087 versus 741/1,087 for aggregate F-ST, but won only 10–7 on 17 F-ST disagreements and lacked season-stable or statistically decisive superiority. It is therefore suitable as a pre-existing directional challenger, not as automatic promotion evidence.
4. **Generic football contrarianism is rejected.** PURE/market disagreement, football unanimity, reputation and large score-margin disagreement all failed as standalone override rules.
5. **Strict market-path and richer expected-lineup information are prospective assets.** Repository governance explicitly prohibits reconstructing historical T-60/T-45/T-30 market paths or richer 2022–2024 lineup state from later information.
6. **2025 personnel state is the narrow historical exception.** The repository qualifies T-120 2025 depth-chart state and a 2025 practice-state reconstruction with stable identity and conservative timing proof. That supports a one-season regime-shock experiment while requiring an explicit one-season evidence limitation.

## External evidence mapped to Candidate 2

### Structural change should alter adaptation strength, not trigger broad refitting

Dynamic paired-comparison and state-space sports models allow team strength to evolve over time. Cattelan (2013, *JRSS C*, DOI 10.1111/j.1467-9876.2012.01046.x) reviews dynamic Bradley-Terry approaches in which abilities change during a season.

Macrì & De Martino (2026, *Journal of Big Data*, DOI 10.1186/s40537-026-01486-6) use team- and time-specific commensurate spike-and-slab innovation priors: stable periods borrow strongly from the past, while sudden changes receive more diffuse evolution. Their documented changes align with roster/injury events and improve out-of-sample Brier performance in NBA data.

**LevLine implication:** event-conditioned flexibility is a materially different theory from Candidate 1's generic outcome-residual persistence. Candidate 2 should look for observable structural discontinuity and remain strongly incumbent-preserving elsewhere.

### QB state is a high-leverage personnel regime variable

Hoffer & Pincin (2019, *Journal of Sports Economics*, DOI 10.1177/1527002519832060) estimate NFL player point-spread values using sportsbook information and find quarterbacks dominate player values.

This does **not** authorize hand-coded QB point values. It supports the preregistered decision to treat QB1 identity change and a qualified QB practice DNP state as high-leverage **regime indicators** whose role is gating, not assigning probability points.

### Betting markets aggregate information during the week

An NFL intra-week market-efficiency study reports increasing information content from early-week to game-time lines while still finding some inefficiencies and evidence consistent with superior analysts: Gandar et al.-style NFL intra-week analysis, *International Review of Financial Analysis* / ScienceDirect PII S0927539813000509.

Krieger & Davis (2024, *Journal of Economics and Finance*, DOI 10.1007/s12197-023-09656-5) study NFL line movement and market visibility across 2007–2021, supporting the premise that market movement is an information-aggregation process.

Simon (2024, *Management Science*, DOI 10.1287/mnsc.2022.00456), in detailed MLB line sequences, finds that betting forecasts are usually reliable but do not always incorporate information monotonically and can overreact.

Older informed-trader work in football/basketball markets also finds that portions of opening-to-closing movement can contain information not explained by public variables.

**LevLine implication:** market-path shock is scientifically plausible, but the repository does not possess an equivalent historical strict-PIT multi-book path for the 2025 Candidate 2 target. Candidate 2 V1 therefore excludes it. It remains a prospective-only follow-on channel and cannot be backfilled from closing lines.

### David Sasser — useful public workflow signal, not an algorithm specification

David Sasser's current public college-football board presents model-projected score/line together with the market **Open** and **Current** line and model picks. Publicly observable 2026 Week 3 examples show the board explicitly preserving model-versus-market context and line movement.

Public source: https://www.davidsasser.com/cfb

No public material inspected here establishes Sasser's exact update algorithm, injury weighting, state-space equations or a validated weekly retraining method. Candidate 2 therefore borrows only the professional-practice idea of keeping model state and market state separately visible; it does not claim to reproduce Sasser.

## Change-point / concept-drift interpretation

Candidate 2 treats a personnel discontinuity as an exogenous **change indicator**, not proof of a directional winner edge. Direction comes from the independently reconstructed component-resolved challenger. This is deliberately conservative:

`F-ST incumbent -> near-boundary disagreement -> qualified structural shock -> allow component side`

The shock gate answers "is the old state potentially stale?" The component model answers "which side does the frozen football information favor?" Neither channel alone is sufficient.

## Evidence hierarchy for requested Candidate 2 signals

- **QB state:** strongest historically testable personnel regime channel in 2025.
- **OL discontinuity:** testable from T-120 rank-1 depth-chart turnover; used as a structural continuity signal, not an injury diagnosis.
- **QB final-practice DNP:** testable for 2025 under the qualified reconstruction; used only as a shock flag.
- **Other high-impact player availability:** valuable in theory but historical role weighting is not equivalently qualified across 2022–2025; excluded from V1.
- **Strict market path / book breadth:** strong prospective hypothesis, historical V1 unavailable.
- **Component disagreement:** usable as frozen directional information; cannot trigger a switch alone.
- **Coach/scheme/transaction regime:** conceptually valid but no equivalent frozen historical point-in-time event ledger exists for V1.
- **Rest/travel/weather:** plausible modifiers with mixed evidence; excluded from V1 to avoid feature soup.

## Falsifiable prediction

If the regime-change theory is useful, the shock-gated component switches should outperform:
1. frozen F-ST on the exact paired sample;
2. the component-resolved challenger used globally; and
3. the boundary + component-disagreement control without a shock requirement.

If the shock gate does not improve switch quality, or if any gain is driven by one team/week/channel or is threshold-fragile, the Candidate 2 mechanism is not supported.

## Scientific boundary

Even a positive 2025 point estimate is not multi-season confirmation. Qualified regime features exist for one historical target season, so a positive result can at most justify **prospective shadow consideration**, never production promotion.

## Addendum — David Sasser GitHub audit

The public GitHub account linked from David Sasser's site was inspected directly.

Relevant repositories found:

- `davidsasser/BettingModel`
- `davidsasser/NFLTotalModel`

### `BettingModel`

The public NFL line scraper is old and should not be treated as the implementation behind the current 2026 college-football board. It is nevertheless informative about Sasser's market-data workflow.

The code:

- pulls NFL moneyline, spread and totals;
- timestamps the collection;
- preserves individual sportsbook observations rather than only one consensus number;
- explicitly parses Pinnacle, 5Dimes, Heritage, Bovada and BetOnline;
- stores book-specific prices/lines in separate fields.

This is directly relevant to LevLine's existing strict-PIT multi-book architecture: professional modeling practice here treats market identity, line type, book identity and observation time as separate data, which is stronger evidence for **preserving market microstructure** than the public website alone.

It does **not** establish:
- a current Sasser model architecture;
- a Bayesian/change-point updater;
- injury or QB weighting;
- weekly model retraining;
- historical efficacy of following or fading line movement.

Therefore no Candidate 2 V1 threshold or feature is changed from this audit.

### `NFLTotalModel`

The public README describes a historical-game training approach for NFL totals and an intended holdout test after Week 6. The repository is incomplete and does not provide evidence of a finished adaptive weekly winner model.

### Current Sasser CFB board versus public GitHub

The current `davidsasser.com/cfb` board displays model projected score, opening line and current line. The public repositories inspected do not expose a clearly corresponding 2026 CFB model implementation. The current site therefore remains useful as evidence of model-versus-market workflow, while the older `BettingModel` repository provides concrete code evidence that Sasser has historically preserved book-specific market observations and timestamps.

### Candidate 2 implication

This strengthens the **future prospective market-shock lane**, especially:
- opener/current delta;
- exact quote timestamp;
- per-book movement;
- movement breadth;
- dispersion;
- stale-versus-fresh book state.

It does not alter `ADAPTIVE-REGIME-SHOCK-GATE-V1`, because the preregistered Candidate 2 historical V1 lacks an equivalent strict-PIT 2025 multi-book path and is already frozen.

