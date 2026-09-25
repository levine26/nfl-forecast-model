# ATS-JSIP-V1 Preregistration Amendment 001 — Inner-Sample Floor

**Status:** FROZEN PRE-RESULT  
**Controls:** `PREREGISTRATION.md`, Section 9 ambiguity only  
**Target-season candidate scores generated before this amendment:** NONE

The initial preregistration required the implementation to register a minimum-row requirement before target scoring but did not itself specify the number. This amendment closes that discretion before implementation or target-season scoring.

## Frozen rule

For every inner rolling-origin fit used to select `df`, `scale`, or `alpha`:

- minimum eligible training rows = **100**;
- the validation season must contain at least one eligible row;
- inner seasons that fail either condition are mechanically omitted and reported;
- if no qualifying prior inner validation season remains for an outer target season, that outer season fails closed;
- no fallback parameter set may be invented from target-season evidence.

The value 100 is inherited from the already-frozen ATS Next-Generation Q1/Q2 chronology machinery (`MIN_INNER_TRAIN_ROWS = 100`) rather than selected using `ATS-JSIP-V1` target performance.

All other provisions of `PREREGISTRATION.md` remain unchanged.
