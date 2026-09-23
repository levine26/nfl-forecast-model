# ATS Economics and EV Contract

Status: FROZEN BEFORE RESULTS

## 1. American odds to break-even probability

For negative American odds `-a`, `a>0`:

`p_break_even_decisive = a/(a+100)`.

For positive American odds `+a`, `a>0`:

`p_break_even_decisive = 100/(a+100)`.

At -110:

`p_break_even_decisive = 110/210 = 11/21 = 0.5238095238`.

At +100, break-even is 0.5.

Zero or malformed American odds are invalid, not coerced.

## 2. Risk/win normalization

For a unit risk stake (`R_bet=1`):

- at negative `-a`, net win `W_bet=100/a`;
- at positive `+a`, net win `W_bet=a/100`.

Equivalent dollar-risk conventions may be used if the same formula is preserved.

## 3. Push-aware EV

For model probabilities `p_win`, `p_push`, `p_loss` that sum to one:

`EV = p_win*W_bet - p_loss*R_bet`.

A push returns stake and contributes zero profit/loss.

A wager is positive EV iff that quantity is strictly >0.

Because `p_win+p_loss=1-p_push`, the decisive conditional win probability is:

`p_win_decisive = p_win/(p_win+p_loss)`

when the denominator is positive. Positive EV is equivalently:

`p_win_decisive > p_break_even_decisive`.

Thus non-zero push mass changes the unconditional win probability required for profitability even though the decisive break-even ratio comes from the quoted price.

## 4. Home and away sides

Q2/Q3 canonical probabilities are home `cover/push/loss`.

For the home ATS wager:

- win = home cover;
- push = push;
- loss = home loss.

For the away ATS wager:

- win = home loss;
- push = push;
- loss = home cover.

The price used must correspond to the exact side being evaluated. Opposite-side juice must never be accidentally applied.

## 5. Paired no-vig price signal

When both spread-side prices are captured at the same line/horizon/book:

1. convert each American price to raw implied probability;
2. normalize each by the sum of the two raw implied probabilities.

This creates a paired no-vig market price signal.

It is not used as the model's true probability, and it is not computed from one side alone.

## 6. Standard -110 reference quantiles

The Q1 quantiles `10/21`, `1/2`, `11/21` are frozen theoretical references motivated by the symmetric standard -110 continuous/no-push decision boundary.

They do not override actual price. If the quoted side is -120, +105, etc., wager EV uses that actual price.

## 7. Historical rows without spread-side price

If historical price is absent:

- actual-price EV is `NOT_AVAILABLE_SOURCE_BOUNDARY`;
- actual-price ROI is `NOT_AVAILABLE_SOURCE_BOUNDARY`;
- the positive-EV-at-quoted-price subset is unavailable;
- no missing price is filled with -110.

A standardized -110 **sensitivity analysis** may be reported, provided every table/field labels it as synthetic price sensitivity rather than observed market economics.

## 8. Realized wager return

With unit risk:

- win profit = `W_bet`;
- push profit = `0`;
- loss profit = `-1`.

For a set of wagers:

`ROI = sum(realized_profit) / sum(risk)`.

If risk is normalized to one per wager, denominator is number of wagers. If actual dollar risk differs, preserve the explicit risk amount.

ROI is secondary and can never select a historical model or threshold.

## 9. Best-side decision

When both side prices are valid, compute EV for home and away separately. `best_side_EV` is the larger EV and `best_side` is the corresponding side. If equal, deterministic tie rule is `NO_WAGER` for positive-EV selection and home-first only for descriptive ordering.

No same-game two-sided wager is counted as two independent ATS decisions in the primary selective evaluation.

## 10. Half-point and whole-number mechanics

- Half-point spread: structural `p_push=0`.
- Whole-number spread: retain exact integer push mass from Q2/Q3.
- Quarter points/nonstandard split-line propositions are outside V1 and are not rounded.

## 11. Alternate lines

If Q2 provides a PMF, alternate-line probabilities can be computed mechanically. But an alternate line is not an actionable wager without its own corresponding quoted price. Do not combine probability at one line with juice from another.

## 12. CLV economics

A closing/later market comparison is valid only if:

- candidate decision line/price is timestamped at the declared horizon;
- later line/price is separately timestamped after the decision and before kickoff;
- no later quote enters the earlier prediction.

CLV is reported separately from realized EV/ROI.

## 13. Selection prohibition

No Phase-2 model family, feature, calibration rule, blend or threshold may be selected by realized profit, ROI, ATS hit rate, or a search over American-price cutoffs. Economics are evaluated after the probability model is frozen by proper scores.