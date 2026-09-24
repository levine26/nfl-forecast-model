# PHASE 5 SCIENTIFIC SYNTHESIS

Program: `LEVLINE_ATS_FRONTIER_V2`

Phase-5 historical survivor count: **`0`**.

Formal dispositions:

- `FV2-HIST-M3-DSSM-01` → `REJECTED`.
- `FV2-HIST-M4-DMARGIN-01` → `REJECTED`.

These decisions are bound to canonical workflow `36025444929`, artifact `10820397832`, artifact digest `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`, the accepted code/config/data hashes, and the canonical M3/M4 OOF hashes. No completed-2026 outcomes were inspected or used.

## Candidate synthesis

### M3 — dynamic football state

The frozen M3 question was whether a compact chronology-safe dynamic offense/defense/QB state could add information after conditioning on the market. It did not.

- primary candidate-minus-null CPL delta: `+0.0006706323752636532` (worse);
- 95% week-block interval: `[-0.00031937461835433245, +0.0016556867645020252]`;
- descriptive probability favorable: `0.0889`;
- all four outer seasons unfavorable;
- `DYNAMIC_NO_QB` outperformed the full model by approximately `0.0002656685` log-loss;
- full candidate calibration slope was materially degraded versus null under the frozen Phase-5 rule;
- red-team/chronology checks passed.

Scientific conclusion: this frozen dynamic-state correction did not establish incremental football information beyond the historical market benchmark. The negative finding is preserved. It does not justify removing QB post hoc and relabeling the no-QB ablation as a survivor.

### M4 — discrete NFL scoring representation

The frozen full M4 candidate produced a large, stable proper-score improvement versus the strong Student-t null:

- primary candidate-minus-null integer-margin log-score delta: `-0.08267169914295289`;
- 95% week-block interval: `[-0.10748698706212485, -0.05796293485132338]`;
- favorable in all four outer seasons;
- numerical/tail audit: `PASS`;
- calibration-relative gate: `PASS`.

However, the frozen ablation result is decisive:

- conditional scale only versus null: `+0.00012506107970626913`;
- constant-scale key mass versus null: `-0.08271839184340689`;
- full minus constant-scale key mass: `+0.00004669270045401389`.

The simpler preregistered `CONSTANT_SCALE_KEY` component reproduces slightly more than the full candidate gain while conditional variance modeling adds no value. The frozen `EVALUATION_PROTOCOL.md` therefore requires rejection of the full candidate identity. The result is scientifically useful but cannot be converted into a survivor by renaming the ablation after seeing the evidence.

## What V2 learned

### Dynamic football state

A compact latent offense/defense/QB correction around the market did not add reliable incremental proper-score information in the 2022–2025 development set. This closes the tested `FV2-HIST-M3-DSSM-01` version. It does not prove all dynamic state-space models are futile, but further work would need genuinely new information or a new preregistered mechanism rather than parameter rescue.

### QB state

Within M3, the preregistered QB component worsened the primary score relative to `DYNAMIC_NO_QB`. This weakens the tested hypothesis that this particular prior-game QB latent state adds information after the market has already incorporated quarterback information. It does not invalidate prospective M2, whose scientific object is different: a timestamped expected-QB-value information delta relative to contemporaneous market movement.

### NFL discrete scoring and key numbers

V2 found strong historical evidence that an integer-margin distribution with explicit mass adjustment at 0/|3|/|7| fits realized NFL margins substantially better than a smooth constant-scale Student-t null on the development population. This is a representation finding, not proof of a betting edge. Because it emerged inside a preregistered ablation of the rejected full M4 candidate, it remains `FUTURE_VERSION_HYPOTHESIS_ONLY`.

### Conditional variance

The frozen conditional-scale specification added no primary-score value. `CONDITIONAL_SCALE_NO_KEY` was slightly worse than the strong null, and adding conditional scale to the key-mass representation made the full candidate slightly worse than `CONSTANT_SCALE_KEY`. The tested V2 conditional-variance mechanism is therefore closed for this candidate version.

### Dynamic market-state research

Historical M1 remains blocked by point-in-time data qualification. Phase 5 does not alter that finding. The existing prospective-only identity `FV2-PROS-M1-MARKETSTATE-01` remains legitimate for future timestamped data capture under its frozen prospective contracts, independently of the rejected M3/M4 historical candidates.

### Prospective QB-delta research

`FV2-PROS-M2-QBDELTA-01` remains a prospective-only identity. Phase 5 neither promotes nor rejects it because its required point-in-time information-delta data were not part of the historical M3/M4 evaluation.

## Permanently closed for this V2 historical candidate version

- `FV2-HIST-M3-DSSM-01` as frozen;
- post-hoc removal of QB to rescue M3;
- new M3 latent dimensions/process-variance changes based on Phase-4 results;
- `FV2-HIST-M4-DMARGIN-01` as frozen;
- the tested conditional-scale mechanism inside M4;
- automatic promotion of `CONSTANT_SCALE_KEY` as M4-v2 or any equivalent renamed survivor;
- M3+M4 combinations, stacks, blends, or ensembles derived from these results;
- ATS/ROI-driven survivor selection;
- retrospective calibration rescue.

## What the evidence does not establish

- no historical durable betting edge is established;
- no production-readiness claim is supported;
- no Phase-6 historical Frontier candidate exists;
- no inference is made from completed-2026 outcomes;
- no claim is made that all future market-state, player-state, dynamic-state, or discrete-margin research is exhausted.

2022–2025 remain development/non-pristine evidence. Any future key-mass-only candidate requires a new identity, new preregistration, fresh governance, and a legitimate future validation path.