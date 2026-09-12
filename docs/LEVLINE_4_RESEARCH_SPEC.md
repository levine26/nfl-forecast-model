# LevLine 4.0 Research Specification

Status: **research-only / preregistered / no production authorization**

LevLine 4.0 is a research program to maximize honest pregame NFL win-probability quality while preserving calibration, auditability, computational efficiency, and rollback safety. It does not mutate the frozen `F-ST-01-FROZEN-2026` production model, its T-120 history, or Sunday Signal publication behavior.

The machine-readable contract is `research/levline4_prereg_v1.json`.

## 1. Executive conclusion

The strongest current evidence does **not** support building LevLine 4 as a larger football-first model. The highest-value research direction is an information-timing upgrade around a strong betting-market prior:

1. preserve the immutable T-120 F-ST lock as the accountability benchmark;
2. capture genuine T-60, T-45 and T-30 multi-book market snapshots;
3. use the official game-day inactive information available around T-90 as contemporaneous player state;
4. test player/lineup information only as a small residual correction to the same-horizon market;
5. explicitly test de-vig, consensus and calibration methods rather than assuming more flexible transformations are better;
6. promote nothing until a prospective paired evidence gate is satisfied.

If raw late multi-book market consensus is the best calibrated probability after prospective testing, that is an acceptable LevLine 4 probability backbone. The research objective is accuracy, not forcing a proprietary adjustment to exist.

## 2. Why change the information horizon

NFL Football Operations documents a 90-minute pregame officiating meeting at which the clubs' Game Day Administration Reports, including inactive lists, are exchanged. A T-120 final lock therefore necessarily precedes a major discrete information release.

This does not prove that T-30 is optimal. Sports-market research and LevLine's own evidence require the horizon to be treated as an empirical question. More information can improve forecasts, but late markets can also become noisy or overreact. LevLine 4 therefore preregisters T-60, T-45 and T-30 as final-horizon candidates while retaining T-120 as the immutable incumbent.

**Working operational hypothesis:** T-45 may offer a useful balance: it is after the T-90 inactive release and allows time for market digestion, source retries, validation and publication. This is a hypothesis, not a selected horizon.

## 3. Existing LevLine evidence that constrains the design

### 3.1 The market is already the hardest benchmark

The current Phase 2 walk-forward market-reliance study selected 100% market weight in every held-out season from 2022 through 2025. On the common 1,087-game historical comparison, raw market probability produced Brier `0.210199` and winner accuracy `0.676173`.

A richer market-plus-football residual increased winner accuracy to roughly `0.6817` but worsened Brier relative to raw market. In large PURE-versus-market disagreement games, market probability was materially better than PURE on both winner accuracy and Brier. This argues for market-primary architecture and against aggressive model overrides.

The historical market dataset is closing-market data, not genuine matched T-minus snapshots. It cannot honestly answer whether T-60, T-45 or T-30 is best. That question requires prospective capture.

### 3.2 Several plausible football-first ideas have already failed LevLine's OOS gates

Existing research has rejected or blocked simple player value, unit continuity, EWMA matchup interactions, fixed market residuals, margin-informed probability, dynamic latent team strength, and the first coherent joint score-distribution candidate. The joint score-distribution candidate reached higher raw winner accuracy but worsened both Brier and margin MAE.

These results do not imply that player or score information is useless. They imply that new information must demonstrate incremental probability value beyond a strong market prior rather than receive weight because it is intuitively football-relevant.

### 3.3 The frozen F-ST historical metrics need correct interpretation

The registered F-ST historical evidence is a chronological OOS architecture evaluation: each held-out season is scored by a stack trained only on prior seasons. That is the appropriate historical model-performance estimate.

Applying the final target-2026 frozen coefficients back across 2022-2025 produces a different, somewhat better Brier score because those seasons contributed to the final meta-model coefficient fit. That is a useful reconstruction backscore, not a replacement for the chronological OOS benchmark. LevLine 4 will keep those quantities explicitly separate.

## 4. Two-clock architecture

LevLine 4 research uses two clocks.

### Clock A: accountability

- Horizon: T-120
- Model: `F-ST-01-FROZEN-2026`
- Status: current immutable production forecast of record
- Purpose: historical continuity, governance, apples-to-apples 2026 forward testing

### Clock B: final-probability research

- Horizons: T-60, T-45, T-30
- Status: research-only shadow forecasts
- Purpose: determine whether a later information set can produce a materially better final pregame probability

No Clock B result may rewrite a Clock A lock.

If a LevLine 4 candidate is eventually promoted, the product should preserve both provenance records: the historical T-120 accountability prediction and a distinctly timestamped final probability.

## 5. Candidate architecture

### 5.1 L4-MKT-H — same-horizon multi-book market prior

For each eligible book at each horizon:

1. verify sportsbook identity and freshness;
2. capture both sides of the moneyline;
3. convert odds to implied probabilities;
4. remove vig using the preregistered method;
5. create a robust cross-book consensus;
6. retain source count, maximum freshness and dispersion as diagnostics.

The initial robust consensus is median probability in logit space because it is resistant to one stale or aberrant book. The experiment must preserve book-level rows so alternative consensus methods can be evaluated without losing provenance.

De-vig candidates:

- basic proportional normalization;
- Shin method where numerically valid;
- power method where numerically valid.

Published cross-sport evidence favors Shin over basic normalization in many bookmaker/sport pairs, but LevLine will not assume that result transfers to two-way NFL moneylines. Same-horizon NFL evidence controls.

### 5.2 L4-FST-H — frozen F-ST transform at a later market horizon

Use the registered F-ST coefficients unchanged, replacing only the market input with the same-horizon research market probability. The nested PURE signal remains unchanged.

This candidate asks a narrow question: does the proven frozen transformation add value when supplied a later market state?

It is not a historical matched-horizon backtest, because the old 2022-2025 market series is closing data and the frozen coefficients were not estimated against T-60/T-45/T-30 snapshots.

### 5.3 L4-PLAYER-OFFSET — player/lineup residual correction

The player layer must not compete with the market from scratch. Its form is conceptually:

`logit(p_final) = logit(p_same_horizon_market) + delta_player`

The existing LevLine expected-lineup system is the correct substrate. Preserve its six units:

- QB
- skill
- offensive line
- pass rush
- run defense
- secondary

Use only point-in-time fields such as modeled player value, replacement value, expected role share, lineup value lost/gained, replacement burden and uncertainty.

At a post-T90 horizon, contemporaneous official inactive information should convert much of binary availability uncertainty into known active/inactive state. Uncertainty remains in role, limitations, workload and realized performance.

Hard restrictions:

- no current-game actual snaps;
- no post-kickoff participation;
- no retrospective inactive status learned after the forecast timestamp;
- no postgame player-value updates;
- no manually tuned player point adjustments chosen from 2026 results;
- unresolved player identity or source chronology fails closed.

A major design concern is double counting. If an inactive player caused the market to move, a player correction cannot automatically add the same estimated effect again. The candidate must prove that player-state features contain residual information *conditional on the same-horizon market probability*.

### 5.4 L4-CAL — explicit calibration candidates

Calibration is a candidate, not a compulsory post-processing step.

Retain identity calibration as the baseline. Test beta calibration and, only after an adequate sample gate, isotonic calibration. Calibration maps must be trained only on chronologically prior out-of-sample predictions. A map cannot be fitted and evaluated on the same 2026 outcomes.

This policy is intentionally conservative: published calibration research shows that flexible or misspecified calibration can make a well-calibrated forecast worse.

### 5.5 L4-WEATHER — secondary winner-probability ablation

Weather infrastructure is useful, particularly for score and total forecasts, but it receives no automatic winner-probability weight. Test point-in-time forecast wind, precipitation, temperature and contemporaneous roof status only after venue/source receipts pass. It enters the winner model only if it improves Brier beyond the same-horizon market.

## 6. What is deliberately not core LevLine 4

Dynamic latent team strength, a joint score-distribution model and a large neural network remain research lanes, not presumed production components.

Dynamic team strength has strong statistical precedent, but LevLine's own first candidate failed its OOS gate. The first coherent score-distribution candidate also failed primary probability and margin gates despite improved winner accuracy. Large neural architectures are not justified by the current game-level sample size and should be reconsidered only if the project acquires materially richer tracking-scale data.

## 7. Evaluation framework

Primary metric: **Brier score**.

Secondary metrics:

- log loss;
- winner accuracy;
- calibration intercept;
- calibration slope;
- reliability by probability bucket;
- sharpness;
- candidate-minus-same-horizon-market Brier;
- candidate-minus-T120-incumbent Brier.

Winner accuracy is descriptive. It may not override a failure on probability quality.

Every statistical comparison is paired at the game level and respects NFL time structure. Use week-block bootstrap intervals and leave-one-week-out recomputation. Horizon comparisons use the intersection of games having valid snapshots at all horizons under comparison.

Preregister diagnostic slices such as:

- QB status change;
- major expected-lineup value loss;
- large T120-to-post-inactive market movement;
- high cross-book dispersion;
- large model-market disagreement;
- extreme weather;
- favorite-probability bucket.

Slices explain performance; they do not rescue a failed aggregate gate.

## 8. Prospective promotion gate

No promotion decision before at least:

- 200 eligible graded games; and
- 14 distinct NFL weeks.

For a model-adjusted LevLine 4 candidate:

1. candidate minus frozen T-120 F-ST Brier must be negative, with the 95% paired week-block bootstrap upper bound below zero;
2. candidate must demonstrate incremental value against the **same-horizon** raw market consensus if LevLine intends to claim a model adjustment improves forecasting;
3. log loss and calibration must corroborate rather than materially contradict the Brier result;
4. the aggregate advantage must remain coherent under leave-one-week-out evaluation;
5. source coverage/freshness and identity gates must pass;
6. promotion is never automatic.

A special case is permitted: if raw late market consensus is clearly the best probability forecast, LevLine may use that consensus as its final probability backbone while retaining proprietary modeling for diagnostics, score forecasts and explanation. That outcome is scientifically preferable to knowingly degrading the probability for branding reasons.

## 9. No-hindsight rules

LevLine 4 will not reconstruct a historical T-45 sample from closing lines, use final inactive lists to pretend a historical forecast knew them, or use later player participation to fill missing pregame state.

Completed 2026 outcomes may grade preregistered frozen candidates. They may not be used during an active evaluation to add interactions, change thresholds, alter feature definitions, rescue a losing candidate, select a preferred horizon, or repeatedly refit until a result becomes favorable. A material architecture change requires a new candidate ID and a new prospective evaluation period.

## 10. Efficient implementation order

### Lane 1 — timing/market

Capture T-120/T-60/T-45/T-30 same-game snapshots, preserve per-book rows, audit freshness and source count, and compare horizon-level Brier prospectively.

### Lane 2 — inactive/player state

Ensure official inactive state is captured with timestamp provenance, then build confirmed-lineup/expected-role aggregates through the existing player-impact engine. Focus first on QB and high-role changes, but do not hard-code position weights from intuition.

### Lane 3 — market construction

Run proportional/Shin/power de-vig and consensus ablations without changing the candidate after outcomes are visible.

### Lane 4 — residual model

Only after player coverage is adequate, fit a market-offset player residual using historically valid point-in-time rows. If comparable historical rows are insufficient, shadow prospectively rather than fabricate labels.

### Lane 5 — calibration

Measure calibration before changing it. Introduce beta calibration only when a chronologically independent training/evaluation split exists.

### Lane 6 — secondary models

Keep weather, margin/total distributions and score simulations independent. Promote them into the win-probability path only through successful ablation evidence.

## 11. Scientific basis

Representative sources motivating the program include:

- Song, Boulier & Stekler (2007), *International Journal of Forecasting*, doi:10.1016/j.ijforecast.2007.05.003 — in their NFL sample, the betting line outperformed statistical systems and experts.
- Strumbelj (2014), *International Journal of Forecasting*, doi:10.1016/j.ijforecast.2014.02.008 — de-vig methodology and bookmaker source identity affect odds-derived probability accuracy.
- Glickman & Stern (1998), *Journal of the American Statistical Association*, doi:10.1080/01621459.1998.10474084 — dynamic NFL team strength can be modeled coherently with a state-space approach, although LevLine's own candidate must still pass OOS evidence.
- Kull, Silva Filho & Flach (2017), *AISTATS*, PMLR 54:623-631 — beta calibration provides a principled alternative to logistic calibration and preserves the identity-map possibility.
- Timmermann (2006), *Handbook of Economic Forecasting*, doi:10.1016/S1574-0706(05)01004-9 — forecast combinations often help, but estimation error can make sophisticated estimated weights inferior to simpler combinations.
- Wang, Hyndman, Li & Kang (2023), *International Journal of Forecasting*, doi:10.1016/j.ijforecast.2022.11.005 — modern review of forecast combinations, including probabilistic combination, calibration and the persistent combination puzzle.

## 12. Current working hypothesis

The architecture with the highest expected value is currently:

`late multi-book market consensus`

plus, **only if prospectively additive**,

`small market-offset player/lineup correction`

followed, **only if independently justified**,

`conservative calibration`.

T-45 is the leading operational hypothesis but is not selected. T-60 and T-30 remain equal-status preregistered candidates until the prospective evidence resolves the timing question.
