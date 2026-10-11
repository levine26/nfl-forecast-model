# CONTINUE HERE — LevLine Betting Lab

## User directive / scope

User wants a serious scientifically evaluated NFL wagering research system handling moneyline, spread, total, touchdowns, yardage props, parlays, round robins and teasers, with a $45 session cap and no production promotion without explicit approval. **Do not build an injury-report integration**. Every implementation must be recorded with evidence for subsequent chats.

## Last verified local implementation

- Local package: `betlab`, v0.3.0-research. Original v0.1 snapshot lives outside this package in the earlier session and remains unmodified.
- B01: quote normalization, actual odds arithmetic, pushes, moneyline/TD/player-market grading, bookmaker settlement contracts and joint-ticket arithmetic.
- B02: point-in-time historical evaluation, CLV quote checking, calibration, ROI and season-week block bootstrap; qualified historical quotes not yet supplied.
- B03: TD and yardage trainable candidates with strict prior-result publication-time feature shift; **the tests use fabricated samples**, so there is no claimed NFL accuracy.
- B04: explicit correlated outcomes across legs of same game, toy shared-pace scoring/TD simulator (uncalibrated), wallet/portfolio distribution.
- B05: conservative paper stake and $45 risk caps, explicit lack-of-evidence abstention; no execution.
- B06: docs, ledger and CLI.
- B07A: timestamp/contract-provenance adapter and create-only SHA256 snapshot receipts; Alexandria per-book subquotes remain explicitly unqualified without their own timestamps.
- B07A-CORRECTION1: make snapshot ID include provider, filters, receipt timestamp and raw SHA so repeated unchanged data at different capture times can be archived separately. Earlier receipt remains append-only.
- All local tests: see actual latest test result and receipt; no claims about remote CI without confirmation.

## Commands

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m betlab.cli ledger
python -m betlab.cli demo --samples 2000
```

## Current scientific status

`ENGINEERING_IMPLEMENTATION_READY_FOR_EXTERNAL_DATA_QUALIFICATION`, but `REAL_NFL_MODEL_UNVALIDATED`, `BOOK_PRICE_DATA_NOT_PIT_QUALIFIED`, `NO_PROVEN_POSITIVE_EV`, `LIVE_BETTING_DISABLED`.

The 2022–2025 LevLine history is *development/nonpristine*, not an untouched holdout. Prior ATS nextgen Q1 and Q3 were rejected against market-only comparators; Q2 had invalid numerical endpoint support. Do not resurrect those candidates or call the toy score simulator a calibrated fix. The winner model F-ST currently in production is market-heavy and not a spread/TD betting model.

## Exact next steps

1. GitHub PR #697 opened from `research/betting-lab-v02-20261010` at commit `6d82e5577546c542865fbfb2706fe7562f5eb6ee`; verify its checks and update PR with B07A. Do not claim merge without remote confirmation.
2. Acquire/source-qualify actual 2022–2025 pregame bookmaker spread/total/moneyline, TD and prop snapshots and 2026 prospective snapshots with timestamps; reject reconstructed pregame prices.
3. Implement a source adapter to frozen quote model (manual/current, The Odds API or Alexandria where provenance/licensing is established), with append-only protected snapshot receipts.
4. Build empirical key-number/score distribution using training-only data, fit and calibrate on separate years/weeks; evaluate over the market-only null using heldout proper scores and exact market economics.
5. Fit and evaluate TD and yardage models on archived NFL player opportunities; do not copy the CHZN1 public 2025 holdout as LevLine validation. Independently reproduce method and compare to baseline.
6. Implement sportsbook-specific teaser and same-game parlay push/price contracts; market quote must identify a real, tradeable operator price. Neither synthetic line nor fixed 0.75 correlation haircut establishes EV.
7. Prospective paper-track all wagers and no-bets from exact pregame cutoff; report with uncertainty and compare to simple market selections. No promotion without express approval.

## Data and prior open-source reference

- Repo `levine26/nfl-forecast-model`, production winner `F-ST-01-FROZEN-2026`.
- Read `research/ats-nextgen/PHASE3_EVIDENCE_SYNTHESIS.md`, `research/ats-nextgen/ATS_ECONOMICS_AND_EV_CONTRACT.md`, `research/LEVLINE_ALEXANDRIA_PIT_FEASIBILITY_2026_10_07.md` before any new model tests.
- Open-source: `github.com/CHZN1/nfl-anytime-td-model` (30 prior-only features, RF/HGB/XGB, 2024 selection/2025 holdout; its parlay multiplier of .75 is an arbitrary heuristic, not joint fit); `github.com/JMutammara/NFL` (market-relative two-stage edge pipeline; audit code/data before borrowing); `github.com/nflverse/nflreadpy` data interface. Do not assume any makes money.

## Recording process

Any completed implementation has an immutable line in `docs/IMPLEMENTATION_LOG.jsonl` and documented acceptance tests. Never delete previous entries; append a correction with a new ID if earlier evidence was wrong. After a merged PR, add an integration receipt listing exact merge SHA and CI check IDs. On interruption record remaining concrete blockers here.

## 2026-10-10 operational MVP continuation

B07B-MVP added `betlab/live_board.py`, `tests/test_live_board.py`, `docs/TOMORROW_RUNBOOK.md` and `fixtures/manual_quote_template.json`. Run actual pregame research board with `python -m betlab.cli board --slate ../../outputs/this_week.csv --quotes /private/quotes.json --outdir /private/outputs`, from the `research/betting_lab` root. The quote template is intentionally synthetic and not executable as a live source; substitute verified actual direct-book quotes with as-of timestamp and verified kickoff. Board is research-only with no positive-EV eligibility. See the runbook. Explicitly never treat 25%/50% scenario probabilities as validated. Local unit test count at this addition: 41. PR #697 branch `research/betting-lab-v02-20261010` must pass full CI before merge.

## 2026-10-10 late-night B07C — existing LevLine research bridge

User explicitly asked for the existing research to produce **Sunday model opinions**, even though true profitability is not validated. Added `betlab/levline_scout.py`, `tests/test_scout.py`, and `python -m betlab.cli scout`. The new CLI takes canonical `outputs/this_week.csv`, optional `outputs/status.json`, and `--date`, writes immutable per-market full-slate watchlists, and never asserts sportsbook quotes or positive expected return. It includes existing ATS NextGen negative results and prior F-ST historical results; no historical refit. Tested with an actual-source reduced-column snapshot (GitHub blob `81351dd037e2608c230d248961ae26f0cff3d859`), preserving MARKET_FRESHNESS_UNKNOWN. Source includes 13 scheduled Sunday games and excludes Thursday/Monday. Any future chat must fetch fresh canonical forecasts before kickoff. **User requested injury-report integration omitted.** See `docs/TOMORROW_RUNBOOK.md` and sample `reports/*.scout.md`.

The screenshot-based prices in conversation are NOT timestamp-qualified live quote API records. Never fabricate them in the manual quote engine. Next: exact-head CI review, merge PR #697 only on required green, record integration SHA, and begin actual prospective paper evaluation against available book quotes.


## B07D — Critical separation of moneyline versus spread/total (2026-10-10)

See [`docs/SCOUT_MARKET_SEPARATION_CORRECTION.md`](SCOUT_MARKET_SEPARATION_CORRECTION.md) for the supersession receipt. F-ST outright winner probabilities **never determine** ATS cover rates. Spread and total scenario probabilities use independent margin/total forecasts, with integer push approximations and no profitability or calibration guarantee. Old Scout B07C reports are superseded; use newly generated market-specific v0.3.2 output. Local 59-test suite passed. Research-only PR #697 remains CI-gated; no production model changes or injuries.


## Latest scope override — B08A / External prop sourcing (2026-10-10)

For Sunday, DO NOT run multi-year touchdown or yards history. Focus on ML, ATS and game totals. Code in `betlab/historical_games.py` supports 2021–2025 *if real pre-kickoff prediction records exist*. Existing frozen chronological F-ST headline covers 2022–2025 only; historical new fair profitability remains unavailable without time-qualified book odds. External prop vendor registry/comparison contract in `betlab/external_props.py`; provider priors are not calibrated weights and no output should be considered bettable. Read docs B08 sprint, vendor strategy, Sunday operating contract first. Apply existing separated ML/ATS scout corrections. Commit research only, wait for CI, append B08 receipt.

## B08B — 2022–2024 game markets, no 2021 requirement

User waived 2021. Added `betlab/frozen_oof_audit.py`, `tests/test_frozen_oof_audit.py`, and CLI `frozen-oof-audit` for 815 matched archived 2022–2024 candidate OOF games. Source paths and exact run command are in `docs/ROADMAP.md`. Markets are separated: outright ML (binary ties excluded), margin ATS (with pushes), totals (with pushes). Source bookmaker horizons are opaque; NO wager ROI. Current F-ST historical 2022–2025 series is DIFFERENT and not to be aggregated with these candidates. `python -m unittest discover -s tests -q` passed 75 locally. Publish isolated research branch with implementation ledger, repeat full GitHub CI on exact head, merge only if green. No historical props or TD. 2026 Sunday Scout is not blocked by retrospective testing.

## B08B result publication (2026-10-11)

Existing research-only OOF B08B audit **RESULT COMPLETE** from original 815 matched 2022-2024 game rows (two tied games excluded from ML binary scoring). Result receipt at `research/betting_lab/reports/b08_sprint/B08B_OOF_2022_2024_RESULTS.json`, explanatory Markdown next to it. Reproducible evaluator `betlab/frozen_oof_audit.py` uses original repository source files, season-before training and OOF assertions. Core pooled metrics: market ML 68.2657% vs A0 62.9766% on 813 non-ties; margin MAE market 9.418405 vs A0 9.882509; total MAE market 10.120859 vs A0 10.386912; A0 spread 386W/401L/28P. These were historical development candidates, *not* current F-ST ML, and not historical profit data; do not pool F-ST and A0/B0/C0. Original B08B ledger implementation receipt retains pre-publication status by append-only rule; the separate `B08B-OFFLINE-OOF-RESULT-2022-2024` ledger entry records result publication.