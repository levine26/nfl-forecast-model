# LevLine Winner vs ATS Fair-Line Value Contract

## Purpose

LevLine now treats two different forecasting questions as different outputs:

1. **Who is more likely to win the game?**
2. **Which side offers value against the sportsbook spread?**

These answers are allowed to disagree.

A team can be the more likely outright winner while its opponent is the better ATS side. Example: if LevLine expects Green Bay to win by 3 but the sportsbook requires Green Bay to win by more than 6, the coherent outputs are:

- outright winner: Green Bay;
- LevLine ATS model line: Green Bay -3;
- market line: Green Bay -6 / Atlanta +6;
- ATS value side: Atlanta +6.

This is not contradictory. It is the fundamental distinction between predicting a winner and pricing a point spread.

## Canonical production semantics

The official winner remains driven by the frozen F-ST production win-probability path. This change does not refit or replace F-ST.

The ATS model line uses the already-produced independent margin forecast:

`ats_model_margin_home = expected_margin`

The canonical repository `spread_line` is expected home margin, so:

`ats_home_edge_points = expected_margin - spread_line`

Decision rule:

- positive edge -> home ATS side;
- negative edge -> away ATS side;
- exact numerical equality -> `NO_EDGE`;
- missing model margin or market line -> `UNAVAILABLE`.

The picked team's sportsbook spread is derived from the canonical expected-home-margin representation:

- home pick -> `-spread_line`;
- away pick -> `+spread_line`.

No edge threshold is fitted from results in this contract. The rule simply identifies which side lies on the favorable side of LevLine's fair margin.

## Public forecast fields

Contract v1.1 adds:

- `ats_model_margin_home`;
- `ats_model_spread_home`;
- `ats_market_margin_home`;
- `ats_home_edge_points`;
- `ats_edge_points`;
- `ats_pick_team`;
- `ats_pick_market_spread`;
- `ats_status`;
- `ats_pick_agrees_with_winner`;
- the corresponding nested `signals.ats` object.

The probability-derived presentation margin remains available for interpreting the official winner probability, but it is no longer the only public concept of a line. It must not be confused with the independent ATS model line.

## Scientific boundary

This policy corrects a forecast-product semantics problem: ATS selection is no longer forced to equal the outright winner.

It does **not**, by itself, prove an ATS edge. ATS accuracy depends on whether the independent margin forecast is sufficiently well calibrated relative to the market. Historical and prospective evaluation therefore remain separate scientific tasks.

No completed-2026 result is used to choose the ATS side rule or tune a threshold. Production winner-model coefficients are unchanged.

## External design reference

David Sasser's public sports-forecast presentation demonstrates the same conceptual separation: his published model line can forecast one team to win while his ATS model pick takes the opponent at a larger market spread. LevLine implements the concept independently using its own margin forecast and canonical market representation; no Sasser source code is copied or required.
