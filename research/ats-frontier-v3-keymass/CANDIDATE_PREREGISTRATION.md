# Candidate Preregistration

## Identity and question
`FV3-PROS-KMASS-01`: Does a market-centered, constant-scale, tail-safe discrete Student-t margin model with fixed key-mass locations `0, ±3, ±7` improve prospective integer-margin probability quality versus the same model with no key-mass offsets?

## Candidate
For integer margin `m`, base mass is `F(m+0.5)-F(m-0.5)`. Multiplicative weights are `exp(gamma0)` at 0, `exp(gamma3)` at |3|, `exp(gamma7)` at |7|, and 1 elsewhere. Normalize analytically over the full unbounded integer lattice. No hard support, clipping, endpoint folding, skew, mixtures, conditional scale, football features, or extra key numbers.

## Strong null
Identical T-120 center, Student-t df, constant scale, bin integration, chronology, and CPL translation, with all gammas equal zero.

## Freeze
Scientific design frozen `2026-09-24T19:04:04Z`. After freeze, only documented operational bug fixes that do not alter the hypothesis are permitted.