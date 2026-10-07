# LevLine Phase 3 — Legacy Tie-Label Contract Audit

**Status:** RESEARCH-ONLY EVALUATION QUALIFICATION, no retuning and no production change  
**Date:** 2026-10-07  
**Linked result:** [EVALUATION_REPORT.md](EVALUATION_REPORT.md)  
**Governance:** The 1,087-row / 741-correct frozen benchmark is retained *unaltered* as the preregistered **legacy binary-label estimand**. The strict tie-excluding winner estimand is **not reproduced** by the current A/B/C execution.

## Finding

The recovered frozen F-ST training panel and 2022–2025 target contain tied regular-season games encoded as `home_win=0` (home loss), although a tie is **not** an away win. This is consistent with the historical production feature builder's binary expression `home_score > away_score`; the immutable panel should **not** be silently relabeled in-place. Existing `research/LEVLINE_4_EVALUATION_GOVERNANCE_V2.md` specifies ties must be excluded from binary winner and proper-score grading. Consequently the 1,087-row paired records are valid *reproductions of the legacy label contract*, but are **not strict tie-excluded evaluations**.

The three known 2022–2025 ties (source: [Pro-Football-Reference Overtime Ties](https://www.pro-football-reference.com/friv/nfl-ties.htm)) are:

| game_id | Actual result | Legacy `home_win` | Frozen F-ST p(home) | A p(home) | B p(home) | C p(home) |
|---|---|---:|---:|---:|---:|---:|
| `2022_01_IND_HOU` | HOU 20–IND 20 | 0 | 0.246605389085 | 0.253189238723 | 0.240898879718 | 0.257934977375 |
| `2022_13_WAS_NYG` | NYG 20–WAS 20 | 0 | 0.431286792852 | 0.391371824587 | 0.422432667634 | 0.465760373941 |
| `2025_04_GB_DAL` | DAL 40–GB 40 | 0 | 0.225136047154 | 0.263820424037 | 0.234603094771 | 0.270541961232 |

All three are predicted away by F-ST and A/B/C and **incorrectly credited as winner picks** by the legacy binary target.

## Result-preserving, *descriptive only* sensitivity

Remove the above three rows **only at the scoring stage**, keeping every frozen prediction and coefficient exactly as saved. This is **not** a tie-excluded refit, so do not reinterpret these as a new OOS baseline or a newly preregistered challenger.

| Model | Legacy correct / 1,087 | Static drop-ties correct / 1,084 | Static drop-ties delta to F-ST |
|---|---:|---:|---:|
| Chronology-clean F-ST | 741 | 738 | — |
| A `MKT-COMP-RESIDUAL-V1` | 730 | 727 | −11 |
| B `MARGIN-RESIDUAL-WIN-V1` | 737 | 734 | −4 |
| C `EARLY-STATE-SHRINKAGE-V1` | 749 | 746 | +8 |

The *ranking and switch differences are unchanged* for this particular static sensitivity because every model agreed on each tie's predicted side. **However, 2020–2021 and 2022 tied-game labels may also appear in model-fitting histories.** A true strict binary-tie-policy run requires a new before-result contract, a clean refit on only non-ties in every historical training fold, an independently regenerated F-ST comparator on the same rows, and properly updated confidence intervals and proper scores. Do not silently reframe the old 741/1,087 as a tie-excluded score.

## Scientific disposition

The initially frozen legacy protocol is reproduced and immutable. A remains **REJECT**, B remains **REJECT**, C remains **INCONCLUSIVE** on that protocol; the tie-excluding production-governance standard is an explicit **unresolved estimand qualification**. It does not justify opening a new candidate, changing features/thresholds, or production promotion. A future strict-tie analysis must be separately frozen and use 2022–2025 only, with 2026 outcomes excluded from model selection.

The earlier Phase 1–2 early-week F-ST slice values (~164 in W1–4, ~241 in W1–6) are labeled *frozen-coefficient* in that older document, whereas this execution uses **season-forward F-ST** (~167 and ~243). These are nonidentical baselines; exact early-week reconciliation remains an audit requirement, not evidence of a winner-picking edge.
