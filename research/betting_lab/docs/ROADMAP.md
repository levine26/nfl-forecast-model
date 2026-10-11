# LevLine Betting Lab — Master Roadmap and Phase Register

**As of 2026-10-10** · Repository target `levine26/nfl-forecast-model` · Separate research-only program.

| Phase | Name | Current status | Acceptance and remaining work |
|---|---|---|---|
| B00 | Evidence inventory / v0.1 snapshot | BASELINE ARCHIVED | V0.1 local prototype has 9 passing tests; no validated edge |
| B01 | Contract pricing and settlement | CODE COMPLETE — TESTED | Moneyline, spreads, totals, TD, player props; quote age and pushes; need operator contract certification |
| B02 | Historical evaluation | CODE COMPLETE — NO QUALIFIED DATA | Outcome-blind chronology guard, proper scores, ROI, CLV, bootstrap; qualify truly timestamped data before historical runs |
| B03 | Player TD and yards candidates | CODE COMPLETE — SYNTHETIC SMOKE ONLY | Trainable logistic/gradient boosting + deterministic pregame feature shifts; source archival and real model evaluation pending |
| B04 | Correlated market construction | ENGINEERING PROTOTYPE — NOT CALIBRATED | Explicit joint scenario ticket pricing, teaser/round robin and portfolio, demo joint TD/score generator; calibrate game score/TD joint distribution and compare to no-edge benchmark |
| B05 | Allocation and reliability | CODE COMPLETE — PAPER MODE ONLY | Hard $45 cap, per-game exposure cap, abstention, optional conservative fractional Kelly, qualified-model gate; validate risk policy on sealed real out-of-time outcomes |
| B06 | Reproducible packaging and handoff | CODE COMPLETE — TESTED | Standalone CLI, scientific protocol, roadmap, immutable receipt ledger, instructions; GitHub PR/review/publish outstanding |
| B07 | Point-in-time provider qualification | B07A PARTIAL — CODE TESTED | SHA256 immutable capture and source adapter in place, with as-of-specific capture IDs (B07A-CORRECTION1); verify real source contracts/timestamps/licensing and build production-quality data archive (B07B) |
| B07B-MVP | Tomorrow pregame quote board | CODE COMPLETE — 41 LOCAL TESTS PASS | Current LevLine CSV + directly time-stamped two-sided operator quotes; market-only vs 25%/50% LevLine sensitivity; create-only JSON/Markdown report. **Not a live feed or validated edge**. |
| B08 | Historical real-data comparative backtest | NOT STARTED | Fixed pre-result evaluation spec, market-only vs betting candidates, ROI / CLV / calibration by market, leakage audit |
| B09 | Prospective weekly paper betting | NOT STARTED | Snapshot before games, immutable prices, grading after games, append-only performance receipt. No wager execution |
| B10 | Production promotion review | BLOCKED | Requires prospective proof AND explicit user approval; never automatic |

## Execution plan for continuation

1. Lock/merge isolated engineering foundation after CI passes; do not touch protected production surfaces.
2. Qualify a source archive that truly captured each bookmaker quote at the decision horizon; implement fresh-data ingestion and price/source receipts before opening an outcome dataset.
3. Preregister target markets and train/validation/holdout splits, baseline comparisons and economic/no-bet acceptance criteria.
4. Develop/score a market-calibrated, discrete game score and player TD joint distribution. Compare with simple market priors and opponent/team usage. Keep experiment IDs fixed.
5. Retest the player TD and yardage candidates on source-qualified historical snapshots; report raw counts, log-loss/Brier, ROC-AUC/PR-AUC, reliability, calibration slope, baseline delta with intervals; include selection/coverage/dropout failures.
6. Run correlation, bookmaker-specific parlay, teaser and round robin evaluation using actual quoted settlement and odds. Stress every bet combination and record worst plausible return.
7. Start immutable weekly shadow picks; record forecast/version/book/line/timestamp/units before kickoff; evaluate CLV and realized ROI only after games.
8. Only consider production promotion after pre-defined performance thresholds and explicit approval.

## Rules for every future implementation

- **Before:** read `docs/HANDOFF.md`, `docs/SCIENTIFIC_PROTOCOL.md`, `docs/ROADMAP.md` and `docs/IMPLEMENTATION_LOG.jsonl`; inspect current main and active PRs. Do not restart V1 research or change frozen models.
- **During:** edit only isolated betting-lab research paths, lock pre-result method, write meaningful tests, prefer reproducible artifacts and market-only baselines.
- **After each implementation:** append an immutable JSONL receipt (`id`, `date`, `status`, `scope`, `files`, `proof`, `limitations`, `next`), update this roadmap and handoff, run tests, commit to isolated branch, open/update PR and cite commit/CI IDs. `IMPLEMENTATION_LOG` may append records, never overwrite old statuses.
- **If interrupted:** write blockers and the next exact runnable command in `HANDOFF.md`; never claim tests or merges that have not actually happened.
- **Never:** place a wager automatically; promote models without approval; import odds lacking pregame provenance; turn reference -110 outcomes into claimed actual ROI; fabricate results; cite synthetic model figures as NFL prediction accuracy.

## B07C — existing LevLine evidence scout, late October 10

**Status: LOCAL CODE COMPLETE, 48 UNIT TESTS, ACTUAL-SOURCE SUNDAY SMOKE REPORT.** `betlab/levline_scout.py` + CLI `scout` uses actual frozen F-ST win probabilities, market-home implied probabilities, expected margin, expected total, and embedded market reference spreads/totals. Known model research (F-ST nonconclusive incremental winner edge, ATS NextGen all rejected and 48.77% legacy ATS hit rate) is embedded as an explicit evidence-limit ledger, **not** smuggled in as calibrated profitable probabilities. Three independent ranked market tables, market-specific/outlier/missing-price flags, $0 stake status and immutable SHA-256 report. No injuries or sportsbook auto-scraping. This makes an immediate Sunday model watchlist possible; B08/B09 remain uncompleted and required for scientific claims.

**Next integration:** update current isolated PR #697 (research only), run latest exact-head CI, merge if all green, record merge receipt. For tomorrow, refresh and run `scout` before the desired kickoff, inspect actual bookmaker lines, optionally run `board` with independently captured timestamps, and archive/grade all paper picks prospectively. Do not assign a numeric expected betting hit rate to scout watchlists.


## B07D — Critical separation of moneyline versus spread/total (2026-10-10)

See [`docs/SCOUT_MARKET_SEPARATION_CORRECTION.md`](SCOUT_MARKET_SEPARATION_CORRECTION.md) for the supersession receipt. F-ST outright winner probabilities **never determine** ATS cover rates. Spread and total scenario probabilities use independent margin/total forecasts, with integer push approximations and no profitability or calibration guarantee. Old Scout B07C reports are superseded; use newly generated market-specific v0.3.2 output. Local 59-test suite passed. Research-only PR #697 remains CI-gated; no production model changes or injuries.


## 2026-10-10 B08A Sunday scope compression

User directed focus on **tomorrow-ready ML/ATS/totals historical auditing**, explicitly **exclude historic TD/props tests**. B08A provides no-refit, chronological per-game evaluator and imports already verified 2022–25 F-ST results; 2021 same-method OOF remains unavailable. B08B qualified historical per-game source joins remain to do. External TD/yards delegated to separate *provider comparison contract* (CHZN1, JMutammara, Custom Venom, GameDay Analytics; StartWho market-only), with zero assumed live predictions absent authorization and source records. Exact handoff: `docs/B08_SPRINT_GAME_MARKETS.md`, `docs/EXTERNAL_PROP_PROVIDER_STRATEGY.md`, `docs/SUNDAY_2026-10-11_PRIORITY.md`. **No production changes; no automatic stakes.**

## B08B — User-approved 2022 start and paired archived OOF comparisons (2026-10-11)

User explicitly authorized beginning historical evaluation in **2022** rather than making 2021 compulsory. Scope is game-market ML, ATS and totals only. New `betlab/frozen_oof_audit.py` and CLI `frozen-oof-audit` compare 2022–2024 archived A0/B0/C0 OOF against original baseline files on the exact same 815 game IDs, including source/provenance assertions, season-before training-gate, quoted-market-vs-model margin and total comparisons, moneyline proper scores, per-season metrics and push-aware spread/total selections. Exclude tied games from *binary ML accuracy and proper scores* but retain them in ATS/totals. Check source SHA-256 and treat late/closing market odds as opaque-horizon references; do not report real betting ROI. **This is an audit of archival candidates, not production F-ST and not 2025 game-level forecast reconstruction.** The separate F-ST 2022–2025 chronological historical summary remains authoritative for current winner model context. Historical props and TD tests are deferred; third-party provider comparison is only a vetted schema at this stage.

From repository root, run:

```bash
cd research/betting_lab
python -m unittest discover -s tests -q
python -m betlab.cli frozen-oof-audit \
 --baselines ../../research/spread-points-nextgen/phase3/evidence/BASELINES_2022_2024.csv \
 --oof ../../research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv \
 --out /private/immutable-reports/B08B_FROZEN_OOF_2022_2024.json
```

Do not rerun source outcomes to choose a new candidate or retrospectively tune stake/edge thresholds. Append scientific receipts, and keep production unchanged.