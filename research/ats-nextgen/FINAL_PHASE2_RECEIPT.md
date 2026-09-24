# ATS Next-Generation — Final Phase 2 Receipt

**Status:** PHASE 2 COMPLETE — SCIENTIFIC CLOSEOUT MERGED  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** `0`

## Final closeout identity

The provenance-correct Phase-2 scientific closeout is merged to `main` through:

- corrective merge vehicle: PR #566;
- validated corrective head: `0ceae72f2643cc9b10a6cf35181576d52bb2fdf7`;
- scientific closeout merge SHA: `89f8b4fa48e22554029392b303225e4665b4b673`;
- merged tree: `97086a3e35c6e4c4275662e9ab437cd46a883d2b`.

All eight exact-head workflows on `0ceae72f2643cc9b10a6cf35181576d52bb2fdf7` completed successfully before merge: research firewall, Phase-2 opening gate, Q1 Stage A, Q2 Stage B, Q3 Stage C, Stage-D closeout, repository research validation, and the normal NFL model-refresh validation.

This governance receipt does not alter any candidate result, accepted artifact, result registry, Stage-D uncertainty computation, production forecast, or frozen scientific contract. Phase 3 must create its opening receipt from the final verified `main` head that contains this governance closeout.

## Provenance correction ledger

Phase-2 history contains multiple Stage-D merge vehicles. Their roles are frozen as follows:

- PR #563 merged the earlier regeneration-based Stage-D closeout path. It remains historical repository evidence but is **superseded for Stage-D evidence-loading provenance**.
- PR #564 / branch `research/ats-nextgen-phase2-stage-d-accepted-artifacts` is the **authoritative scientific origin** of the corrected direct-artifact Stage-D result. Its accepted evidence head is `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`.
- PR #564 was later closed unmerged as a merge vehicle because current `main` had diverged after #563.
- PR #565 was based on the superseded regeneration-path closeout and was closed unmerged. It is not authoritative.
- PR #566 applied exactly the corrected, already-validated Stage-D closeout blobs on top of then-current `main` and is the **authoritative Phase-2 scientific closeout merge vehicle**.

Numerical Stage-D evidence did not change during this provenance correction. The correction changes which evidence-loading path is authoritative: final uncertainty comes from the immutable accepted Q1/Q3 GitHub Actions artifacts, not candidate regeneration.

## Opening data/evidence gate

- PR #559 merge `f43e17ba783e3e389969cd1649889b37bd91afe9`;
- historical seasons 2015–2025 only;
- 2,895 ATS-eligible games;
- 73 pushes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- source-sign contract: `market_home_margin_center = spread_line`, `home_spread = -spread_line`, `ats_residual = margin + home_spread`;
- historical schedule market evidence remains exact-horizon opaque and is not relabeled T-120.

## Q1 — quantile market-residual model

Candidate `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`.

Accepted evidence:

- PR #560 merge `a2581a62e3797a6ac466d614326bc72b7d5a1c57`;
- workflow `35920622523`;
- artifact `10776898518`;
- OOF SHA `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- 1,087 chronology-clean OOF games, 2022–2025;
- Q1 minus M2 mean-three-quantile pinball `+0.0001307887665715768`;
- Stage-D paired 95% CI `[-0.002378435765685505, +0.002555544033066125]`;
- bootstrap probability Q1 better `0.4554`.

**Phase-2 state:** valid negative incremental result. No Q1 rescue is authorized.

## Q2 — discrete key-margin distribution

Candidate `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`.

- PR #561 merge `16859845573c3344ed82ae0b9bd27fa8b891eee4`;
- frozen support `[-75,+75]`;
- material folded endpoint-mass threshold `0.001`;
- observed maximum folded endpoint mass `0.0033487075822347966` during first accepted execution attempt;
- execution failed closed before complete Q2 OOF scoring.

**Phase-2 state:** structurally invalid under frozen V1 support/truncation contract.

There is no accepted Q2 OOF, primary proper-score result, complementarity result, or Q2/Q3 blend. Those cells remain unavailable; Phase 3 may not reconstruct or substitute them.

## Q3 — direct cover/push/loss hurdle

Candidate `ATS-Q3-DIRECT-CPL-HURDLE-V1`.

Accepted evidence:

- PR #562 merge `539081c59e62a5d4dbc0a8f849d8a332424ea06e`;
- workflow `35931071604`;
- artifact `10781521222`;
- OOF SHA `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- 1,087 chronology-clean OOF games, 2022–2025;
- Q3 minus Q3-M2 multinomial CPL log loss `+0.0013157418572419255`;
- Q3 minus Q3-M2 non-push conditional-cover Brier `+0.0006716459171549338`;
- log-loss Stage-D 95% CI `[-0.0015590942193462521, +0.004336647782633088]`, probability Q3 better `0.1842`;
- Brier Stage-D 95% CI `[-0.0007977772384239724, +0.002212922097716785]`, probability Q3 better `0.1851`.

Simple non-push hit-rate diagnostic: Q3-M2 `559/1058 = 52.8355%`; Q3 `552/1058 = 52.1739%`.

**Phase-2 state:** valid negative incremental result — not incremental versus Q3-M2. No Q3 rescue is authorized.

## Stage D — authoritative final evidence synthesis

Scientific origin:

- branch `research/ats-nextgen-phase2-stage-d-accepted-artifacts`;
- PR #564;
- accepted evidence head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588` — SUCCESS;
- contract job `107441314608` — SUCCESS;
- synthesis job `107441551438` — SUCCESS;
- artifact `10783982962`;
- artifact digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

Stage D consumed the accepted immutable Q1/Q3 artifacts directly and verified their full registered hash maps. It used exactly 10,000 paired `(season, week)` bootstrap draws, seed 26, 72 blocks, and two-sided 95% percentile intervals.

Accepted Stage-D artifact hashes:

- paired uncertainty `c6680a25bc6acc17a6b552bd6c9593df166d17c5e2e750e1ebffa7d538ed6f1e`;
- hit-rate intervals `885c4627c814286b76e6ba3e91c34bafd97b2079f4937448b385e7220df720b3`;
- season deltas `28316ccf2e7009f0a9a9f1fe1a5e2f127a7f449dfb5cd04a15e506c7dd15f0bc`;
- summary `d78dcf91965bdb71bea8fbcf0261bbe5ff629e28b0a7538e12ac20e07c1766a9`.

On the verified scientific closeout merge, the immutable Stage-D result registry blob is `c4450bbebd78f383b04d51eb85f1129caa684704` and the direct-artifact Stage-D runner blob is `0696aa9c1715cd3f30299aeaff7380245c2e1ce9`.

The immutable scientific result remains recorded in `PHASE2_STAGE_D_RESULT_RECEIPT.md` and `phase2_stage_d_result_registry.json`; this governance closeout intentionally does not modify them.

## Scientific conclusion entering Phase 3

Phase 2 produced **no positive historical-development candidate result** under the frozen incremental tests:

- Q1: adverse point result versus M2;
- Q2: invalidated before valid OOF performance by its own frozen support contract;
- Q3: adverse point result versus Q3-M2;
- Q2 complementarity/blend: unavailable.

The Stage-D confidence intervals cross zero for the defined Q1/Q3 incremental deltas. This indicates that the development sample does not sharply resolve effects of the tiny observed magnitude. It does **not** convert an adverse point result into a positive result, establish material inferiority, or authorize candidate rescue.

Historical 2022–2025 evidence is chronology-clean development evidence but remains non-pristine because those seasons have informed prior LevLine research.

## Phase boundary

Phase 2 does not assign the final program labels `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`. Phase 3 owns that classification and freeze.

Phase 3 must begin from a verified `main` head containing this governance closeout and must create an immutable opening receipt before classification. It may synthesize only the frozen evidence above; it may not refit, redesign, rescue, rerun historical candidates, inspect completed-2026 outcomes, or alter production behavior.

Phase 4 remains conditional on Phase-3 eligibility and explicit user authorization.
