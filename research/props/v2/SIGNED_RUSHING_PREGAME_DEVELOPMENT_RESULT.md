# LevLine Props 2.0 — Signed Rushing True-Pregame Development Result

Status: **RETROSPECTIVE DEVELOPMENT — REJECTED**  
Primary workflow: `35420676818`  
Contract: `levline-props-v2-signed-rushing-pregame-v0.1.0`  
Production promotion authorized: **NO**

## Question

The earlier component-isolation study showed that signed empirical rushing-event support improved
conditional CRPS when actual event count was held fixed.

This follow-up removed that postgame conditioning:
- V1's full pregame opportunity simulation was retained;
- the exact sampled carry array was preserved for every player;
- V1's player rushing-yards/carry mean and uncertainty were retained;
- only the conditional rushing-yard draw was replaced with signed empirical event residuals fitted
  through season S−1.

Target-game carries and target-game yards were never used to fit or construct the forecast.

## Pooled 2023–2025 result

Paired rushing-yard props: **982**  
Unique games: **230**  
Unique players: **114**

- V1 CRPS: **18.26136**
- signed challenger CRPS: **18.30030**
- challenger minus V1 CRPS: **+0.03894** (worse)
- game-clustered 95% interval: **+0.01676 to +0.06300**

- V1 Fair-Line MAE: **24.90733**
- challenger Fair-Line MAE: **24.93737**
- challenger minus V1 MAE: **+0.03004** (worse)
- game-clustered 95% interval: **−0.02264 to +0.08299**

- V1 80% coverage: **62.22%**
- challenger 80% coverage: **63.14%**
- coverage change: **+0.92 pp**

The coverage safeguard passes, but both primary proper-score / Fair-Line criteria fail.

## By season

| Season | N | Δ CRPS | Δ Fair-Line MAE | V1 coverage | Challenger coverage |
|---|---:|---:|---:|---:|---:|
| 2023 | 279 | **+0.08908** | **+0.11470** | 56.27% | 58.06% |
| 2024 | 628 | **+0.02573** | −0.00239 | 64.65% | 65.29% |
| 2025* | 75 | −0.03703 | −0.01333 | 64.00% | 64.00% |

*2025 is the small genuine-OPEN slice and cannot rescue the pooled / multi-season failure.

CRPS improves in only **one of three** seasons. In 2023 the challenger is materially worse, with a
season-level clustered CRPS interval entirely above zero.

## Scientific disposition

**REJECT P2-DIST-RUSH-PREGAME-V01.**

The signed-support mechanism was useful under actual-event-count component isolation but did not
survive interaction with the full pregame opportunity distribution. That is exactly why the
component-first firewall exists.

Do not:
- tune the residual pool by position using these prop outcomes;
- reweight negative events;
- alter the 250-event fallback threshold;
- blend Gamma and empirical draws based on these results;
- rescue the candidate using the small favorable 2025 slice.

The earlier component result remains scientifically informative: negative rushing-event support is
real, but this particular empirical-residual integration is not an improvement to the full pregame
Props distribution.

No production forecast, Props V1 output, F-ST model, or betting threshold changes from this result.
