# Adaptive Weekly Learning — Candidate 3 final finding

Status: **COMPLETE — INCONCLUSIVE**  
Candidate: **ADAPTIVE-MARKET-PATH-INNOVATION-V1**  
Authoritative preregistration: **52cf402cd33da0e535ef963c7d98f9b4304ea208**  
Production authorization: **NONE**

## 1. Exact candidate tested

Candidate 3 used frozen chronology-clean F-ST as the structural prior and added one genuinely new information channel: same-book market-path innovation between:

- EARLY: latest qualifying sportsbook snapshot in T-2160..T-1440;
- LOCK: latest qualifying sportsbook snapshot in T-360..T-120.

For each common sportsbook:

`delta_book = logit(p_home_lock) - logit(p_home_early)`.

Primary path innovation:

`D = median(delta_book)`.

Primary frozen update:

`logit(P_C3) = logit(P_FST) + 0.50 * D`.

At least five common sportsbooks were required. Missing path state failed closed to exact F-ST.

No Candidate 3 parameter was fitted to 2025 outcomes.

## 2. Why this candidate was chosen

Candidate 1 rejected generic weekly residual learning. Naive weekly F-ST refitting also failed. Candidate 2 produced one favorable regime-shock switch but remained inconclusive.

Market-path / information-arrival adaptation was the strongest orthogonal remaining hypothesis because it introduced genuinely new timestamped market evolution rather than another refit of the same football state.

## 3. PIT-data qualification

Historical source:

- `bobby-king3/nfl-market-movement-tracker`
- release `v1.1.1`
- `nfl_odds.duckdb`
- SHA256 `b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c`

Outcome-blind qualification established:

- 285 archived 2025-season games;
- 38 sportsbooks;
- 0 post-or-at-kickoff rows;
- 278 games with >=5 identical books spanning the early and lock bands in the source audit.

The archive is **not** dense enough to claim exact historical T-120/T-60/T-45/T-30 states. Candidate 3 therefore uses only the preregistered coarse bands.

## 4. Target sample

Primary evaluation sample:

- season: 2025 regular season;
- 272 exact chronology-clean F-ST benchmark rows;
- 264 qualified market paths;
- 8 fail-closed rows;
- path coverage: 97.0588%.

The 2025 historical outcomes were known from prior LevLine research before Candidate 3 began. Candidate 3 path features were not joined/scored against target outcomes before the authoritative preregistration. Therefore a favorable result could never count as prospective validation.

## 5. Frozen F-ST baseline

F-ST on the identical 272-game sample:

- correct: **179 / 272**
- accuracy: **65.8088%**
- Brier: **0.2115784131**
- log loss: **0.6076199189**

## 6. Candidate 3 result

Candidate 3:

- correct: **180 / 272**
- accuracy: **66.1765%**
- accuracy delta: **+0.367647 percentage points**
- Brier: **0.2121303769**
- Brier delta vs F-ST: **+0.0005519638** (worse)
- log loss: **0.6086655021**
- log-loss delta vs F-ST: **+0.0010455831** (worse)

Winner switches:

1. `2025_08_CHI_BAL` — Candidate 3 switched BAL -> CHI and lost.
2. `2025_12_ATL_NO` — Candidate 3 switched NO -> ATL and won.
3. `2025_17_BAL_GB` — Candidate 3 switched GB -> BAL and won.

Switch summary:

- switches: **3**
- Candidate-3-only correct: **2**
- F-ST-only correct: **1**
- switch win rate: **66.67%**
- net winner gain: **+1**

## 7. Statistical uncertainty

Exact McNemar two-sided p-value:

- **1.0**

10,000-draw NFL-week block bootstrap for accuracy delta:

- 95% interval: **-0.7576 to +1.4981 percentage points**
- bootstrap probability delta > 0: **61.52%**

The interval materially includes harm and no gain.

## 8. Market and control comparison

On the 264 path-qualified rows:

- F-ST: **172 / 264 = 65.1515%**
- EARLY market: **172 / 264 = 65.1515%**
- LOCK market: **175 / 264 = 66.2879%**
- latest pre-kickoff market: **175 / 264 = 66.2879%**
- market-trend control: **173 / 264 = 65.5303%**

The all-row level-only control, which updates F-ST using only the later market level rather than the preregistered path statistic, scored:

- **180 / 272 = 66.1765%**
- net gain vs F-ST: **+1**
- switches: **3**
- switch record: **2-1**

Its three switches were different games from Candidate 3's three switches, but it reproduced the same net winner gain.

This fails the preregistered independence test:

> Candidate 3 did **not** demonstrate incremental winner information beyond a market-level update.

## 9. Previous-candidate comparison on 2025

Same 272-game slice:

- F-ST: **179**
- Candidate 3: **180**
- Candidate 2 unchanged: **180**
- component-resolved stack: **179**
- naive weekly refit unchanged: **179**
- Candidate 1 unchanged: **182**

Candidate 1's 2025 slice remains non-promotable because Candidate 1 was rejected across 2022-2025. Candidate 2 remains inconclusive because its entire gain came from one switch. Candidate 3 does not improve the evidentiary state over Candidate 2.

## 10. Robustness / adversarial findings

Preregistered 12-cell grid:

- positive cells: **3 / 12**
- neutral cells: **7 / 12**
- negative cells: **2 / 12**

By lambda:

- 0.25: zero gain in all lock windows;
- 0.50: +1 winner in all lock windows;
- 0.75: zero gain in all lock windows;
- 1.00: -1 winner in the two broader lock windows and zero gain in the strictest window.

Concentration:

- deleting Week 12 erases the gain;
- deleting Week 17 erases the gain;
- deleting ATL, GB, or NO erases the gain;
- a single-game deletion can erase the entire net gain;
- maximum positive team contribution share of the net gain: **100%**.

Book dependence:

- all 37 leave-one-book-out recomputations preserved the +1 net result.

Boundary concentration:

- all three switches occurred within 7.5 percentage points of the F-ST 50% boundary;
- median absolute F-ST distance from 50% among switches: **3.45 pp**.

PIT/leakage checks:

- post-kickoff market rows used: **0**
- LOCK rows later than T-120 used: **0**
- completed 2026 outcomes loaded: **0**
- post-preregistration Candidate 3 retuning: **false**
- production changed: **false**

## 11. Scientific interpretation

Candidate 3 produced a favorable point estimate, but the evidence is too sparse and too fragile to establish a sustainable winner improvement.

More importantly, the preregistered level-only control reproduced the same +1 net winner gain. The 2025 archive suggests that later market **level** contained useful information relative to the F-ST state on some games, but this experiment did not establish that the **path by which the market arrived there** added independent winner-selection information.

Probability quality also moved in the wrong direction: both Brier score and log loss worsened versus F-ST.

## 12. Disposition

**INCONCLUSIVE**

Candidate 3 is not rejected as a completely useless signal because the primary point estimate was +1 winner and leave-one-book-out checks were stable.

It is not promising because:

- only 3 switches occurred;
- week-block uncertainty includes harm;
- one game/week/team can erase the gain;
- the effect exists only at the primary lambda and disappears or reverses nearby;
- probability metrics worsen;
- the level-only control fully reproduces the net winner gain.

No production promotion is authorized.

No automatic live shadow deployment is authorized by this historical result.

## 13. Updated sustainable-accuracy estimate

The evidence does **not** justify raising the program's prior sustainable estimate.

Current research judgment remains approximately:

- central estimate: **~68.3%**
- practical near-term range: **~68.2-68.4%**

This is a research judgment, not a formal confidence interval.

## 14. Canonical reproducibility record

Authoritative preregistration:

- `52cf402cd33da0e535ef963c7d98f9b4304ea208`

Canonical successful workflow:

- run: **35757935130**
- artifact: **10708209825**
- artifact SHA256: **ce64bc2d011acb894e65a7a05273ce897bec76dc14cb9b95b64b3b2dd7d636a8**
- PR-head SHA: **56de02d2e2d20ca39d567c03fc6bbe887c69b71a**
- PR-merge execution SHA recorded by GitHub Actions: **fb6040bfae5380213c8deca13036e8754d358ec1**
- config digest: **de577832d944868c65d3ab562f094bc6c71cee3eff8aee5c91957f6399f686d6**
- market archive SHA256: **b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c**

## 15. Recommended next research step

Do **not** tune Candidate 3 retrospectively.

The next scientifically defensible step is prospective validation of a separately frozen market-information design that explicitly decomposes:

1. market **level** update;
2. market **path** / information-arrival residual conditional on level;
3. qualified player/QB news timing where available.

That prospective design must be frozen before future outcomes and evaluated with immutable prediction locks.

Candidate 4 is **not** started by this closeout.
