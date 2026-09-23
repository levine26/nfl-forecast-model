# Phase 1 Open-Source Model Review

Evidence classes used here:

1. peer-reviewed;
2. reproducible open source;
3. strong technical practitioner evidence;
4. opaque product/system;
5. speculative.

Open-source results are architecture evidence, not proof that the same result transfers to LevLine.

## 1. `greerreNFL/nfelo` — evidence class 2

Current source was inspected directly, including `nfelo/Model/Nfelo.py`, optimizer documentation and the current `nfelotranslation` integration.

### Transferable architecture

- explicit football rating state;
- explicit regression toward market information rather than pretending model and market are independent;
- separate open and close handling;
- conversion of model state to spread/win probability;
- cover/push/loss probability from the same margin-distribution object;
- CLV/open-close concepts kept separate from realized game outcome;
- optimizer documentation that recognizes ATS as noisier than proper probability scores.

### Not copied

No nfelo current parameter, market-regression coefficient, Elo transform, weighting rule or reported performance is imported into LevLine.

### Scientific caution

nfelo is a useful reproducible system, but its internal objective/history differs from LevLine. Its existence supports testing coherent probability/spread/distribution translation; it does not validate LevLine Q1–Q3.

## 2. `greerreNFL/nfelotranslation` — evidence class 2, analyses class 3

Actual implementation inspected:

- `MarginDistributionModel`;
- `BaseDistribution`;
- `Normalizer`;
- `KeyModel` and seasonal fitting/validation paths;
- training/validation analyses.

### Current architecture observed

The package constructs an integer PMF over margins approximately `-75..+75` from a generalized-normal continuous base, discretizes it, adds key-number excess, clamps and renormalizes while enforcing probability/spread constraints. The base exposes a shape parameter with Gaussian as a special case and heavier tails for lower generalized-normal shape.

Its normalizer handles whole-number and half-number lines differently, including explicit push mass for integer spreads. Seasonal training infrastructure reconstructs key-number state using only earlier seasons.

### Practitioner analyses inspected

The repository's current analyses support several useful hypotheses:

- generalized-normal/heavy-tailed form can fit empirical NFL margins better than a simple Gaussian;
- key-number excess is not uniform and is strongest at familiar football margins;
- key-number behavior can vary by era/season;
- key-number excess can depend on distance from the expected center;
- within-spread price information is not shown by that analysis to be a large universal signal.

These are **reproducible practitioner findings**, not peer-reviewed conclusions and not LevLine results.

### Transfer to Q2

Transfer the concepts only:

- integer PMF;
- fixed bounded range;
- heavy-tail comparison;
- explicit key-number excess;
- whole/half-point push logic;
- season-forward fitting.

Do not import shipped beta, tie probability, key ratios, scale, normalization constants or any other fitted value.

## 3. `ShamgarBN/nfl-bet-engine` — evidence class 2 for code; reported results class 3

The repository was inspected beyond its README:

- `model/scores.py`;
- `model/simulate.py`;
- `model/spread_direct.py`;
- `model/ensemble.py`;
- `model/calibrate.py`;
- `backtest/walkforward.py`.

### Useful architecture

- separate score/distribution model and direct ATS classifier;
- explicit probability blending;
- attempt at walk-forward evaluation;
- calibration infrastructure;
- feature architecture that combines football state and market context.

This supports the hypothesis that a generative distribution head (Q2) and discriminative ATS head (Q3) may contain complementary information.

### Material methodological weaknesses for LevLine to avoid

1. The direct spread target in current code treats `(margin + spread) > 0` as 1 and everything else as 0, so a push is not modeled as its own outcome.
2. The simulation computes cover probability but does not expose a key-number-aware push probability comparable to Q2's discrete PMF.
3. The simulation architecture uses Normal score draws plus a shared lognormal environment factor; key-number structure is not an explicit distribution component.
4. The backtest implementation described as weekly contains season-level fitting behavior in important paths; labels and documentation therefore require careful reconciliation before treating claims as prospective-style weekly evidence.
5. ATS selection uses expected-margin divergence from the closing line as a conviction score. LevLine has already found that larger model-market margin disagreement is not itself a validated edge.
6. The repository's reported top-decile/full-slate rates are third-party results until independently reproduced under the same source/timing contracts.
7. Its stated CLV proxy is not equivalent to conventional timestamped market CLV.
8. A validation path in the inspected score-residual code appears to reuse training-prediction indexing for an evaluation residual calculation; this is a code-level caution, not a claim about every reported result.

### Transfer decision

Transfer only the **architectural decomposition** Q2 + Q3 + bounded blend. Do not copy its learner stack, feature kitchen sink, thresholds, reported hit rates, calibration choices or selection rules.

## 4. nflverse / Open Source Football ecosystem — evidence class 2

nflverse remains the strongest open foundation for LevLine's schedule, results, PBP and lagged football state. It is suitable for chronology-clean completed-game features but its final historical schedule market fields do not establish exact book, quote timestamp or spread-side juice.

The ecosystem is therefore a football-data and historical benchmark source, not a complete historical sportsbook order-book feed.

## 5. David Sasser — evidence class 4

Current public `davidsasser.com/cfb` pages were revisited. They continue to expose:

- projected scores;
- projected/model line;
- opening line;
- current line;
- ATS pick;
- public straight-up and ATS tracking.

No public source code, feature specification, training chronology, calibration method or reproducible historical data contract was located in this review. Hidden methodology is not inferred.

Transferable observable design concept: keep **model projection**, **market state**, and **bet-selection layer** visibly distinct.

## 6. Open-source conclusion

The strongest cross-project concept is a modular architecture:

`market/football state -> conditional location -> discrete margin distribution -> cover/push/loss probabilities`

plus an independent direct probability head and a tightly controlled blend.

The review does **not** support an unrestricted challenger tournament. It supports the bounded Q1/Q2/Q3 preregistration adopted here.