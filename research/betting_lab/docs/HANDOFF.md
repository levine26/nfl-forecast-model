# CONTINUE HERE — LevLine Betting Lab

## User directive / scope

User wants a serious scientifically evaluated NFL wagering research system handling moneyline, spread, total, touchdowns, yardage props, parlays, round robins and teasers, with a $45 session cap and no production promotion without explicit approval. **Do not build an injury-report integration**. Every implementation must be recorded with evidence for subsequent chats.

## Last verified local implementation

- Local package: `betlab`, v0.2.0-research. Original v0.1 snapshot lives outside this package in the earlier session and remains unmodified.
- B01: quote normalization, actual odds arithmetic, pushes, moneyline/TD/player-market grading, bookmaker settlement contracts and joint-ticket arithmetic.
- B02: point-in-time historical evaluation, CLV quote checking, calibration, ROI and season-week block bootstrap; qualified historical quotes not yet supplied.
- B03: TD and yardage trainable candidates with strict prior-result publication-time feature shift; **the tests use fabricated samples**, so there is no claimed NFL accuracy.
- B04: explicit correlated outcomes across legs of same game, toy shared-pace scoring/TD simulator (uncalibrated), wallet/portfolio distribution.
- B05: conservative paper stake and $45 risk caps, explicit lack-of-evidence abstention; no execution.
- B06: docs, ledger and CLI.
- B07A: timestamp/contract-provenance adapter and create-only SHA256 snapshot receipts; Alexandria per-book subquotes remain explicitly unqualified without their own timestamps.
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