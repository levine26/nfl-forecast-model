# ATS-JSIP-GAUSSIAN-V1 — Preregistration Amendment 001

**Status:** FROZEN PRE-IMPLEMENTATION / PRE-TARGET-SCORING  
**Candidate:** `ATS-JSIP-GAUSSIAN-V1`  
**Original preregistration merge:** `77e7b14a93584f97e2fb677af6eaf4c3e08cd9b3`  
**Target candidate scores inspected before amendment:** 0  
**Completed-2026 outcomes used:** 0

## Purpose

Bind the preregistration's mathematical spread symbols to the repository's already-canonical field semantics before implementation.

The preregistration writes sportsbook home handicap as `L` and market home-margin center as `C = -L`.

The repository's authoritative ATS numerical core defines:

> `spread_line` = expected home margin.

It also grades home ATS cover as:

`actual_margin - spread_line > 0`.

Therefore the exact field mapping for this candidate is frozen as:

- `C = repository spread_line`;
- `L = -repository spread_line`;
- `mu_H = (T + repository spread_line) / 2`;
- `mu_A = (T - repository spread_line) / 2`;
- home Cover iff `M > repository spread_line`;
- Push iff `M == repository spread_line` for an integer line;
- Loss iff `M < repository spread_line`.

This is a notation/field-binding amendment, not a change in market meaning or model direction. It prevents applying the mathematical minus sign twice when consuming the canonical repository field.

All other frozen candidate rules, grids, chronology, metrics, support invariants, and advancement gates remain unchanged.
