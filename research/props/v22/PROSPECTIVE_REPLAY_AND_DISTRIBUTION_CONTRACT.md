# LevLine Props 2.2 — Prospective Replay and Distribution Observability Contract

Status: **PREREGISTERED INFRASTRUCTURE / NO MODEL TUNING**  
Candidate infrastructure version: `levline-props22-replay-bundle-v0.1`  
Purpose: make future frozen Props cohorts exactly replayable for proper distribution scoring.

## 1. Motivation

The frozen Props 2.1 Week 2 cohort preserved point forecasts, Fair Lines and threshold
probabilities, but did not preserve a lossless distribution or a permanently replayable
simulation input bundle. As a result, CRPS, PIT and empirical interval coverage were
scientifically unavailable even though the underlying simulator had generated full Monte
Carlo samples.

Props 2.2 must fix that observability gap **before** any successor calibration or
distribution hypothesis is evaluated.

This contract changes no forecast number, signal, threshold, market input, F-ST output,
or winner-model behavior.

## 2. Replay principle

A Props simulation is considered exactly replayable only when all of the following are
permanently frozen:

1. exact integration manifest JSON for every game;
2. exact manifest-slate JSON and its fingerprint;
3. simulation seed and simulation count for every game;
4. model version and prediction-interval level;
5. exact Git generation-base SHA;
6. SHA-256 fingerprints of the simulator, integration and runner source files at that
   generation-base SHA;
7. source workflow/run identity and frozen forecast timestamp;
8. deterministic archive SHA-256 containing the exact manifest bytes.

The replay bundle is content-addressed. A future evaluator must fail closed if any manifest,
archive, code fingerprint, or provenance value disagrees.

## 3. Why raw simulation arrays are not committed

The Week 2 source run contained 3,439 forecast rows and used 20,000 simulations per game.
Persisting all raw Monte Carlo arrays directly in Git would be unnecessarily large.

The exact Week 2 live audit artifact was about 7.5 MB compressed, while the 15 integration
manifests were about 24.7 MB uncompressed and roughly 1.6 MB compressed. Therefore a
deterministic compressed replay bundle of the frozen manifests is small enough to preserve
per prospective evaluation cohort.

The manifests plus seed, simulation count and exact code revision are the lossless replay
representation. Summary statistics alone are not.

## 4. Required bundle contents

Each cohort replay directory contains:

- `replay_bundle.zip`
- `replay_index.json`

The archive contains, byte-for-byte:

- `manifest_slate.json`
- one `games/<game_id>.manifest.json` per frozen game

The index contains:

- contract version;
- source workflow run;
- live run id;
- generation-base SHA;
- trigger-head SHA when available;
- forecast timestamp;
- archive SHA-256;
- manifest-slate content SHA-256;
- game count and ordered game IDs;
- per-game manifest SHA-256;
- per-game seed;
- per-game simulation count;
- per-game model version;
- per-game prediction-interval level;
- exact source-code SHA-256 fingerprints for:
  - `src/nfl_forecast/challenger_props_simulation.py`
  - `src/nfl_forecast/props_integration.py`
  - `scripts/run_props_research_beta.py`

## 5. Determinism requirements

Archive construction must be deterministic:

- sorted member order;
- fixed archive timestamps;
- no local filesystem metadata;
- exact original manifest bytes;
- deterministic compression settings.

Building the same bundle twice from identical inputs must produce the same archive SHA-256.

## 6. Replay evaluation

A future evaluator may calculate CRPS, PIT, interval coverage, arbitrary-threshold
probabilities and distributional diagnostics only after:

1. verifying the replay index;
2. verifying every archived manifest fingerprint;
3. checking out the exact generation-base SHA;
4. verifying source-file fingerprints;
5. regenerating the simulator from the archived manifest, seed and simulation count;
6. matching regenerated point summaries against the immutable forecast receipt within
   deterministic numerical tolerance.

If point summaries do not reproduce, distribution scores are unavailable rather than
approximated.

## 7. Prospective cohort boundary

Week 2 outcomes may not be used to select replay parameters because replay infrastructure has
no predictive parameter.

For model changes motivated by Week 2 diagnostics, Week 2 remains development/diagnosis only.
The first valid successor evidence must come from an untouched future prospective cohort
(Week 3+) or a separately qualified leakage-free historical holdout that was not used to
choose the change.

## 8. Relationship to future model research

This infrastructure enables, but does not itself authorize:

- support-correct yardage distribution challengers;
- availability/workload mixture challengers;
- live-compatible route/opportunity proxy challengers;
- outcome-free market-microstructure studies;
- calibration or probability-tempering challengers.

Previously rejected hypotheses remain rejected unless a new scientific rationale and new
preregistered specification are created. In particular, the previously tested prop-family
market calibration, FTN residual and NGS residual specifications are not reopened by this
work.

## 9. Production firewall

Replay artifacts are research evidence only.

They must never:

- enter the F-ST winner model;
- alter official LevLine probabilities;
- alter Props forecast values;
- alter market capture;
- alter QA/signal classification;
- expose postgame outcomes to pregame generation.

Any implementation that violates those boundaries fails closed.
