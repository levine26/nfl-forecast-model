# Adaptive Weekly Learning — Candidate 3 evidence review

Status: **pre-outcome design evidence / research only**

Candidate family under consideration: **market-path / information-arrival adaptation**.

## Why this is the strongest orthogonal remaining hypothesis

Candidate 1 showed that generic weekly residual learning and naïve weekly refitting do not improve frozen F-ST winner selection. Candidate 2 showed only a single favorable regime-shock switch and remained inconclusive. The next defensible hypothesis therefore needs genuinely new information rather than another refit of the same state.

The current LevLine 4 ledger already identifies strict point-in-time market path as a high-value prospective lane and already implements T-120/T-60/T-45/T-30 path geometry prospectively. Candidate 3 does not replace that infrastructure. It asks whether an independently archived **historical 2025 market path** can support a one-season, coarse-horizon historical test without reconstructing missing states.

## External evidence

- Adams & MacKay (2007), *Bayesian Online Changepoint Detection*, arXiv:0710.3742. Abrupt changes can be modeled as changes in a sequential generative process rather than by indiscriminate refitting. Relevance: supports interpreting path jumps as potential state changes, not automatically as truth.
- Fischer/Schmal (2025), *Economic Inquiry*, DOI 10.1111/ecin.13258. In 117,174 odds from 32 bookmakers around elite-soccer absence announcements, prices showed initial inertia and lagged reaction. Relevance: player information can arrive in prices over time; path can contain information not summarized by a single level.
- Kang & Salaga (2022), *International Journal of Sport Finance*, DOI 10.32731/IJSF.171.022022.03. Line accuracy improved as information became available and line movement declined as markets converged. Relevance: information release and path dynamics deserve explicit measurement.
- Krieger & Fodor (2013), *Journal of Economics and Business*, DOI 10.1016/j.jeconbus.2013.04.002. Closing lines were more accurate than opening lines in college basketball, but informativeness varied with market composition. Relevance: line movement may encode information or noise; Candidate 3 must test incremental value rather than blindly follow movement.
- Gandar et al. (1998/2002), *Journal of Finance*, DOI 10.1111/0022-1082.155346. Within-period line changes improved forecast accuracy in NBA betting. Relevance: establishes a plausible information-arrival mechanism, not NFL proof.
- Gandar et al. (2005), *Applied Financial Economics*, DOI 10.1080/0960310042000306961. Unexplained college-football line movements were more informative than movements explainable by widely distributed public signals. Relevance: path may summarize latent information, but sport/era transfer is uncertain.
- Wolfers & Zitzewitz (2006), NBER w12083. Markets can aggregate dispersed information. Relevance: supports treating market path as an information process while preserving the need for empirical validation.
- Recent dynamic Bradley-Terry work (Journal of Big Data, 2026, DOI 10.1186/s40537-026-01486-6) uses sparse state-space innovation to capture abrupt team-strength changes. Relevance: supports sparse/shrunken updates rather than continuous high-variance retraining.

## David Sasser review

Current public review found:
- `davidsasser/NFL-BIG-DATA-BOWL-2026` remains primarily a tracking/trajectory Big Data Bowl project, not a public chronology-safe weekly NFL winner-learning system.
- `davidsasser.com/cfb` publicly shows model-projected scores alongside opening/current market lines and model picks. This is useful evidence that model-vs-market context is operationally relevant, but the public page does not document an outcome-independent market-path adaptation algorithm or preregistered NFL winner gate.
- No newer public Sasser repository found in this review materially changes the prior conclusion.

Sasser is therefore supporting context, not methodological authority for Candidate 3.

## New PIT source discovery

Public repository `bobby-king3/nfl-market-movement-tracker` provides a versioned DuckDB archive built from The Odds API historical endpoint:
- 2025 NFL season through Super Bowl;
- four scheduled historical snapshots per day;
- 38 books observed in the qualified relation;
- raw pre-match price/line states, bookmaker identity, capture timestamp and bookmaker update timestamp;
- v1.1.1 release asset SHA256 `b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c`.

LevLine CI independently verified the release hash and audited the database without loading outcomes. The canonical source-audit run is 35756509795, artifact 10708651734.

The source **does not qualify exact T-120/T-60/T-45/T-30 historical claims** because captures occur only four times per day. It **does qualify** a coarse early band (T-2160 to T-1440) and coarse lock band (T-360 to T-120) for the 2025 historical experiment.

## Design implication

Candidate 3 should use:
1. the frozen F-ST probability as structural prior;
2. a robust, same-book market-path innovation only;
3. a fixed shrinkage coefficient chosen ex ante;
4. no fitted threshold and no outcome-trained gate;
5. current market level as a separate control;
6. strict fail-closed missingness;
7. one-season historical evidence treated as discovery/qualification, not production proof.

No completed 2026-season result is authorized for feature, threshold, coefficient, or architecture selection.
