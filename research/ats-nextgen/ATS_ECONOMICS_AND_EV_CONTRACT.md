# ATS Economics & EV Contract

## 1. American odds

For negative American odds `-a` (`a>0`):

- risk `R=a` to win `W=100`;
- no-push break-even probability `p_BE = a/(a+100)`.

For positive American odds `+a` (`a>0`):

- risk `R=100` to win `W=a`;
- no-push break-even probability `p_BE = 100/(a+100)`.

At -110:

`p_BE = 110/210 = 11/21 = 0.5238095238...`.

The complementary probability is `10/21 = 0.4761904762...`.

## 2. Push-aware EV

For model probabilities `(p_win, p_push, p_loss)` summing to 1:

`EV_dollars = p_win*W - p_loss*R`.

Push returns stake and contributes zero profit/loss.

Normalized per dollar risked:

`EV_per_risk = p_win*(W/R) - p_loss`.

A bet is eligible under an EV rule only when `EV_dollars > 0` using the exact side price attached to the same book/line/timestamp.

With pushes, do **not** compare raw `p_win` alone to 52.38%. Equivalent non-push break-even is:

`p_win / (p_win + p_loss) > R/(R+W)`

when `p_win+p_loss>0`.

## 3. Side symmetry

If home probabilities are `(c,p,l)` for cover/push/loss, away probabilities at the opposite side of the same line are `(l,p,c)`.

Do not apply the home-side price to the away-side outcome or vice versa. Every EV row must carry:

- book/source;
- line;
- side;
- American price;
- quote/update timestamp;
- decision timestamp/horizon;
- model probability vector.

## 4. Vig removal

When deriving market probabilities from two-sided moneyline prices, convert both sides to raw implied probabilities then normalize by their sum, consistent with LevLine's existing `add_vig_free_market_prob` behavior.

Spread-side prices are **not** de-vigged by pretending a missing opposite-side price exists. If only one spread-side price is available, it may support that side's direct payoff economics but not a two-sided no-vig fair-probability claim.

## 5. Historical no-price rows

If a historical row has spread number but no qualified spread-side price:

- exact quoted-price EV = unavailable;
- actual-price ROI = unavailable;
- do not fabricate -110;
- optional standardized sensitivity may assume -110 only if labeled `REFERENCE_MINUS110` in every artifact/table/column name.

This reference sensitivity cannot be described as a historical sportsbook ROI backtest.

## 6. Selectivity

Phase 2 may report positive-EV selections only for rows with real qualified price. It also reports fixed top-20% and top-10% pre-outcome edge subsets under `EVALUATION_PROTOCOL.md`.

No repeated search across EV thresholds is permitted.

## 7. CLV

Closing-line value is defined only when there is a legitimate later quote from a comparable market/book/consensus after the decision snapshot.

Model expected-margin disagreement with a closing spread is not, by itself, CLV.

## 8. Quantile relationship

Q1's `10/21`, `1/2`, `11/21` quantiles are decision-theoretic reference points derived from standard -110/no-push economics. They do not override the exact price/push-aware EV equation in this file.