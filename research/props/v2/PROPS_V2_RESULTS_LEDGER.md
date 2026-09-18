# LevLine Props 2.0 — Results Ledger

Status: **CURRENT THROUGH 2026-09-18**

## Frozen V1 benchmark

2023–2025 regular seasons, Weeks 1–18, primary genuine Action Network OPEN population:
- directional accuracy: **51.02%** (2,888 / 5,660 decided non-push props);
- Fair-Line MAE from the frozen diagnosis: approximately **19.18** versus sportsbook OPEN line MAE
  approximately **15.93**.

## Global market-prior residual — development evidence

Rolling-origin 2024–2025:
- N **4,109**, 153 unique games;
- challenger **53.74%** vs frozen V1 **51.23%**;
- paired gain **+2.51 pp**;
- game-clustered 95% interval approximately **+0.14 to +4.91 pp**.

On the 3,002 price-informative rows:
- sportsbook price direction **55.13%**;
- challenger **55.06%**;
- challenger minus market **−0.07 pp**;
- clustered 95% interval approximately **−1.11 to +0.98 pp**.

Probability scores:
- V1 Brier **0.28600**;
- market Brier **0.24608**;
- challenger Brier **0.24621**;
- V1 log loss **0.83248**;
- market log loss **0.68514**;
- challenger log loss **0.68540**.

**Disposition:** market anchoring is a material architecture improvement over V1; V1 residual signal
beyond the sportsbook is not established.

## Generic NGS residual

Fixed-anchor matched comparison:
- NGS residual accuracy approximately **52.26%**;
- matched market+V1 residual approximately **52.23%**;
- difference approximately **+0.02 pp**;
- game-clustered interval spans materially negative to positive values.

**Disposition:** REJECT as established incremental residual signal.

## Generic FTN matchup residual

Fixed-anchor:
- FTN residual approximately **52.21%**;
- matched baseline approximately **52.23%**;
- difference approximately **−0.02 pp**.

2024 rolling comparison was also negative, and probability scores did not improve.

**Disposition:** REJECT generic FTN residual signal.

## Prop-family market calibration

Fixed anchor:
- family-specific **52.49%** vs pooled global residual **53.60%**;
- difference **−1.11 pp**, clustered 95% interval **−2.40 to +0.12 pp**;
- Brier **0.24737** family vs **0.24650** global.

Rolling-origin 2024–2025:
- family-specific **52.74%** vs pooled global **53.74%**;
- difference **−1.00 pp**, clustered 95% interval **−2.19 to +0.17 pp**;
- Brier **0.24672** family vs **0.24621** global.

**Disposition:** REJECT; preregistered gate failed. Permanent record is
`PROP_FAMILY_MARKET_RESIDUAL_DEVELOPMENT_RESULT.md`.

## Dynamic role v0.1 — workflow still completing

2023 full role adjustment:
- paired N **1,549**;
- challenger **51.26%** vs V1 **50.48%**;
- gain **+0.77 pp**;
- Fair-Line MAE **23.77** vs **23.97** V1.

2023 route-only:
- paired N **1,550**;
- challenger **50.77%** vs V1 **50.45%**;
- gain **+0.32 pp**;
- MAE **24.10** vs **23.96** V1 (worse).

2025 full (small genuine-OPEN sample, 16 games):
- paired N **413**;
- directional accuracy tied at **54.96%**;
- MAE **16.73** vs **16.81** V1.

2025 route-only:
- paired N **413**;
- challenger **55.21%** vs V1 **54.96%**;
- gain **+0.24 pp**;
- MAE **16.80** vs **16.81** V1.

2024 jobs remain in progress at the time of this ledger entry. No dynamic-role variant is promoted.

## Prospective shadow

Clean firewall-compliant implementation: **PR #379**.
Frozen candidates:
- market-only no-vig probability;
- market + frozen pre-2026 V1 residual.

No completed 2026 outcome may change the candidate. Grading is evaluation-only.

## Production conclusion

No Props 2.0 architecture is scientifically authorized for production at this point. V1 remains the
published Props model while research and prospective evidence continue.
