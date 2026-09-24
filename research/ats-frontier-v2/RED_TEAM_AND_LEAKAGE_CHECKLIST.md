# RED TEAM AND LEAKAGE CHECKLIST

This checklist must pass before any Phase-4 target score is accepted.

## Market-time failures

- [ ] no post-kick market quote;
- [ ] no equal-kick quote where the contract requires strictly pre-kick evidence;
- [ ] no after-target nearest-neighbor quote;
- [ ] no future market snapshot/interpolation;
- [ ] no opener/close relabeled as a fixed horizon;
- [ ] bookmaker identity preserved;
- [ ] bookmaker aliases/renames do not create duplicate independent books;
- [ ] spread sign/unit tested;
- [ ] side price attached to the correct team/line;
- [ ] moneyline/spread side mapping unit tested;
- [ ] quote age explicitly measured when exact-horizon market data are used.

## Football-state failures

- [ ] no target-game PBP;
- [ ] no target-game realized snaps;
- [ ] no final inactive list backfilled before publication;
- [ ] no eventual starter identity backfilled to an earlier horizon;
- [ ] no gamebook-derived target-game state used pregame;
- [ ] no realized target-game weather;
- [ ] prior-game corrections/publication lag obey chronology;
- [ ] season transitions are explicit;
- [ ] QB replacement identity is timestamp-qualified where M2 is used.

## Modeling failures

- [ ] preprocessing/scaling fit on prior-only data;
- [ ] hyperparameters selected only through frozen chronological inner tuning;
- [ ] no target-outcome architecture selection;
- [ ] no candidate-family search after target results;
- [ ] no post-hoc calibration rescue;
- [ ] no threshold/selectivity fishing;
- [ ] no repeated holdout framing for 2022–2025 development seasons;
- [ ] completed-2026 outcomes absent from fit/tune/design;
- [ ] candidate/null scored on exact common rows.

## M4 numerical failures

- [ ] integer bin mass uses `F(m+0.5)-F(m-0.5)`;
- [ ] PMF normalizes to 1 within `1e-12`;
- [ ] all probabilities finite/nonnegative;
- [ ] cover + push + fail = 1 within `1e-12`;
- [ ] non-integer spread push = 0;
- [ ] integer push maps to correct integer margin;
- [ ] no finite-support endpoint folding;
- [ ] extreme synthetic spread/total cases remain finite;
- [ ] home/away sign reversal synthetic tests pass.

## Required synthetic tests before target scoring

1. **Market horizon test:** quotes immediately before and after a target; selector must choose only the pre-target quote.
2. **Kickoff boundary test:** pre-kick accepted; equal/post-kick rejected under strict source rule.
3. **Book alias test:** renamed aliases collapse to one canonical book without duplicating breadth.
4. **Spread sign test:** synthetic home favorite and home underdog produce expected cover/push/fail sides.
5. **Price side test:** favorite juice cannot be assigned to underdog outcome.
6. **PBP chronology test:** target-game row injected into source must not enter target prediction.
7. **QB leakage test:** eventual starter/snap identity unavailable before horizon must remain unavailable.
8. **M4 tail test:** extreme Student-t parameter combinations retain full mass without endpoint accumulation.
9. **M4 push test:** integer spread maps structural push correctly; half-point spread has zero exact push.
10. **2026 firewall test:** any 2026 completed-outcome row in training/evaluation input causes hard failure.

## Fail-closed rule

Any unresolved checklist failure stops the affected candidate before its target performance is interpreted. A favorable result never overrides a leakage or numerical-contract failure.