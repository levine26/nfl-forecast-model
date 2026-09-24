# ATS Historical Key-Mass Challenger — Canonical Merge Receipt

**Canonical state:** MERGED / CLOSED  
**Repository:** `levine26/nfl-forecast-model`  
**Pull request:** #582 — `Research: canonicalize ATS historical key-mass challenger`  
**Merged to:** `main`  
**Merge commit:** `794dc38fbaf1b2076b6eb8ab66509ee9d207646a`  
**Merged research head:** `7247960295e2e0deae78f47095365b8f4006167e`  
**Pre-merge main head:** `b3bc5c7c01d5e254e85f47195779e2df2cbc5a91`

## Validation against current main

The branch was revalidated against the then-current `main` immediately before merge.

- GitHub reported PR #582 mergeable.
- Live-main drift since the research fork was non-overlapping with the challenger files.
- The final PR diff was confined to isolated research surfaces plus the dedicated research workflow.
- `LevLine research firewall` run `36069749713`: **SUCCESS**.
- `LevLine research validation` run `36069749714`: **SUCCESS**.
- The workflow path was normalized to `.github/workflows/research_ats_historical_challenger.yml` so it complied with repository research-firewall governance before merge.
- No production F-ST or Sunday Signal forecasting files were modified by the PR.

## Canonical scientific result

The historical center challenger tested the accepted constant-scale Student-t key-mass distribution with three location centers on leakage-safe outer seasons 2022–2025, using **1,087** common games.

Primary exact integer-margin log score, lower is better:

| Candidate | Score |
|---|---:|
| `KMASS-MARKET` | 3.8529284697864035 |
| `KMASS-LEVLINE` | 3.852007914481647 |
| `KMASS-BLEND` | 3.8517646735798237 |

Preregistered paired comparisons versus `KMASS-MARKET`:

- `KMASS-LEVLINE`: delta `-0.0009205553047568027`; 95% bootstrap CI `[-0.006094539833178175, +0.004308287264421793]`; favorable in 2/4 outer seasons.
- `KMASS-BLEND`: delta `-0.0011637962065803756`; 95% bootstrap CI `[-0.0024836545264246275, +0.0001601218148759597]`; favorable in 2/4 outer seasons.

Neither non-market center satisfied the frozen advancement gate.

**Canonical disposition: `RETAIN_KMASS_MARKET`.**

This means the validated baseline remains `KMASS-MARKET + constant-scale key-mass`. The numerically lower aggregate score for `KMASS-BLEND` is not promoted because its confidence interval crosses zero and its season-stability criterion fails.

## Key-mass replication

The market-centered key-mass candidate reproduces the accepted V2 constant-key result on all 1,087 common rows. The key-number correction remains materially favorable versus the same-center no-key ablation:

- Market center key-minus-no-key: `-0.08271839184340689`.

This remains the robust accepted mechanism from this line of research.

## Immutable execution evidence

Accepted historical execution:

- Workflow run: `36065686319` — **SUCCESS**
- Validated execution head: `8dbe37008324c6d5d3a69116c897ee599b85e22a`
- Artifact id: `10836511323`
- Artifact name: `ats-historical-keymass-36065686319`
- Artifact digest: `sha256:93b378de840de1ff8e6158f5c9df1da55a84ad3306ea1c695b1fb4537a5a9a59`

Artifact output hashes:

- `CENTER_ARCHIVE_RECEIPT.json`: `114d70f3a1c42ecf1a66c7fe0db3257d1df996fde2dcdfb9edcbf852dd8949c8`
- `OOF_PREDICTIONS_2022_2025.csv`: `94568856d2fdaea26b0ba1e04931f1101f8080b285792775565c95841b936e26`
- `RESULTS.json`: `60554e8c8db69a318f9cce3cdebab977ff36b4458ea058a458621a6bce5f69db`
- `TUNING_AND_BLEND_WEIGHTS.json`: `280834288aedb6f51f5ebeab18a73ee7848eba7c9e19a6f4a642a58edba596ab`

## Firewall / governance receipt

- Completed 2026 outcomes used: **0**.
- Production forecasting behavior changed: **NO**.
- Production authorization created: **NO**.
- Scientific result is now canonical on `main` as research evidence only.
- Any future ATS challenger should compare against the frozen canonical baseline `KMASS-MARKET + constant-scale key-mass` and must pass its own preregistered historical validation before any production consideration.

## Canonical source files

- `research/ATS_HISTORICAL_CHALLENGER_FINAL_RECEIPT.md`
- `research/ats-historical-challenger-result-registry.json`
- `research/ats-historical-challenger/PROGRAM.md`
- `research/results/ats-historical-challenger-20260924/FINAL_RESULT.md`
- `research/results/ats-historical-challenger-20260924/RESULT_REGISTRY.json`

This receipt closes the historical center-challenger branch and establishes the merged result above as the repository’s canonical scientific record for this experiment.
