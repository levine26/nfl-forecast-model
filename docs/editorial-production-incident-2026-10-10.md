# Sunday Signal production editorial incident review — 2026-10-10

**Status:** Active production incident; not launch-ready. This is an engineering evidence record, not a claim that the complete replacement has shipped.

## Evidence examined

* At `main` 26c93c9345bd28bbaa33dd643f0d7bb1fb11c6c5, `outputs/context_source_status.json` reported 14 Groq failed games requiring ChatGPT refresh. The separate editorial acceptance audit reported 0/15 structurally eligible HUMAN Reads, 15/15 rejected, and `article_resolution_verified=false` / `claim_support_verified=false`.
* GitHub Actions `38103143144` failed in the fallback overlay. The log explicitly shows four focused games validated, then `2026_05_CLE_NYJ` rejected for "no concrete tactical action-and-counteraction explanation"; an uncaught `subprocess.CalledProcessError` stopped the remaining targets. This proves the observed fail-fast behavior.
* The same run had no `groq-validated` cache hit, and the last-good restorer raised "no launch-grade historical editorial snapshot covers all 15 roster games." The script proceeded with existing provider/cache data rather than fabricating a complete snapshot.
* On the same branch, `outputs/copilot_media_reads.json` retained only the preceding Week 4 Atlanta–New Orleans item; this is not Week 5 full-slate HUMAN authority.
* The fallback workflow is triggered by every change under `inputs/chatgpt_media/fallback/**` and uses `cancel-in-progress: true`. Several runs immediately preceding `38103143144` concluded `cancelled` after successive one-game payload commits. This is a confirmed ineffective operating pattern, not evidence of a provider bug.
* `inputs/chatgpt_media/fallback/manifest.json` lists the 14 current Groq failure targets. The schema is user-session producer-driven; it is not a credential-backed autonomous API worker.
* The repository's structural source acceptance checks explicitly disclaim article resolution and substantive claim verification. URL shape and publisher-family independence are necessary but not sufficient.

## Root-cause matrix

| Finding | Evidence classification | Consequence | Remediation |
| --- | --- | --- | --- |
| Per-game validator run with `check=True` inside one loop and no collection | **Verified** in ingestion source and run log | First failing game stops slate diagnosis | Batch all game results into structured diagnostics; preserve only accepted normalized candidates |
| No portable same-roster publication-grade snapshot / cache miss | **Verified** in job log | Recovery cannot rely on previous complete HUMAN slate | Persistent authoritative game-scoped accepted records with checksums, schema, source receipts, and retention across refreshes |
| Full-slate gate requires all 15 valid candidates | **Verified** in workflow | Safe fail-closed behavior also delays publication of independent already accepted content | Preserve per-game accepted drafts; publish only a fully consistent release or explicitly represent unavailable articles without claiming completion |
| Every single fallback file commit triggers a new workflow and cancels the previous run | **Verified** in triggers and recent run conclusions | Repeated restarts and quota-consuming work | Debounce/batch changes; separate candidate validation from the one release worker; do not cancel active attempts on unrelated input changes |
| Manifest remains an external ChatGPT-consumer handoff | **Verified** in producer field and scripts | No authentic headless automatic failed-game authoring | Narrow compatibility importer; credential-backed independently executable fallback needed for autonomy |
| Source URLs treated as candidate receipts rather than article-content verification | **Verified** in acceptance report and source policy | Incorrectly asserting factual verification would be unsafe | Add fetch/parse/canonical-URL/claim-support receipts before HUMAN publication |
| Context refresh may impact source state/content independently of accepted provider writing | **Architectural risk supported by separate owners** | Previously accepted prose may be withheld or replaced | Versioned accepted editorial records, freshness flags, explicit invalidation reasons, no delete-on-refresh |
| Concurrent forecast/context/Groq/fallback writes racing main | **Risk confirmed by workflow design; individual race not conclusively reproduced** | Stale or refused publication | Single editorial release writer with immutable canonical input fingerprint and optimistic compare-and-swap |
| Groq daily token quota as cause of this slate's provider failures | **Recorded in authoritative provider status; raw upstream quota response not reverified** | 13 games unable to generate HUMAN text from Groq | Circuit breaker per credential/model with backoff and provider-independent recovery |

## Editorial dependency map (observed current topology)

```text
Canonical forecast & locks (protected)
   outputs/this_week.csv, outputs/status.json, prediction_history.csv
       |                         |
       v                         +--> Sheet sync / Pages numeric cards
 scripts/run_context.py  --> contextual_evidence.json, game_previews.json,
       |                    context_source_status.json
       v
 media discovery / Groq request / per-game focused validator
       | accepted normalized text (ephemeral run/cache)
       v
 outputs/copilot_media_reads.json (historical artifact; not per-game durable authority)
       ^
       |
 inputs/chatgpt_media/fallback/manifest.json + 2026_05_*.json
       |
 scripts/ingest_chatgpt_failed_games.py
       | focused validation -> mixed-raw -> composition
       | -> deterministic paragraph-2 renderer
       | -> full-slate validator -> finalizer
       v
 outputs/copilot_media_reads.json, game_previews.json,
 contextual_evidence.json, context_source_status.json
       |
 sync_market_reads/check -> protected numerical consistency
       |
 git commit/push to main -> dashboard workflow -> GitHub Pages
```

**Data authority distinction:** canonical forecast rows/official locks are numerical authority; verified, versioned accepted game-scoped HUMAN paragraphs should be editorial authority; context and news packets are evidence snapshots; generated two-paragraph Reads and site/Sheet views must be derived and re-renderable. Neither a fallback manifest nor a rendered paragraph-2 field should become numerical or editorial authority.

## A/B/C architecture decision

| Option | Strength | Principal limitation | Judgment |
| --- | --- | --- | --- |
| A: targeted patch | Low immediate risk and quick visible failure diagnosis | Leaves manifests, cross-workflow output ownership, ephemeral caches, quality-proof gaps | Not sufficient as final solution |
| **B: major refactor** | Retains existing strict validator, source policy, canonical renderer, and Groq adapter; replaces state/orchestration and verification boundaries | Requires migration, proof of correctness, shadow operation and controlled cutover | **Selected** |
| C: clean subsystem rewrite | Clean conceptual architecture | Reimplements mature football/source/renderer gates; risky cutover near current slate without verified equivalence | Not justified before B shadow comparison |

### Target system (must first operate in shadow)

1. **Evidence receipts:** per-game verified article records with canonical URL, publisher, published/updated/retrieved times, content snapshot hash, attributed claims, current player/team mapping, and independent publisher family. Reject missing content or unsupported claims; capture individual rejection reasons.
2. **Human draft:** provider-agnostic candidate with stable `game_id`, revision, provider, evidence-receipt hashes, clean headline, 55–100-word football paragraph, qualitative rationale, timestamp, and generation inputs. Groq primary; fallback only when actually configured and quota-safe.
3. **Independent game acceptance:** complete error list per game; immutable accepted entry only after factual, structural, tactical, and source gates. Keep previous accepted revision until replacement passes. Mark freshness separately.
4. **Deterministic render:** join current valid forecast snapshot and accepted editorial by `game_id`, re-render paragraph 2 on legitimate pre-lock number changes; never freeze or let LLM author numerical predictions.
5. **Single release authority:** verify all 15 games and cross-game uniqueness, compare canonical-input hash to current main, write a single validated release snapshot atomically. Hold the last good release on any failure, separately exposing pending/rejected state. Exactly one job is permitted to update public editorial outputs.
6. **Operational recovery:** bounded retry with quota circuit breaker; game-scoped leases/idempotency keys; restore-on-crash from accepted records. ChatGPT manifest importer remains temporary compatibility, **not** claimed as autonomous.
7. **Migration:** shadow build + fault injection + week-5 replay; assert numeric hashes and official locks unchanged; compare quality and provenance against current release. Cut over after rollback rehearsal and required CI/deploy verification; retire competing writers at cutover.

## Engineering work in this PR

The current PR **only** implements the safe first reliability slice: independent, complete game-scoped validation with accurate stderr-derived diagnostics; isolated rejected candidates; a persistent all-game diagnostic report that is explicitly not a publication authorization; CI artifact collection; and regression tests for 2 failures among 15 games. This change neither invents recovery content nor allows partial publication. It does **not** deliver the full selected refactor, permanent accepted-entry persistence, a credential-backed fallback provider, or verified source content.

## Frozen governance boundary

No change in this PR to the F-ST model files, official forecast strategy, locked predictions, grades, official historical rows, diagnostic-margin policy, or challenger research. The next stages must compare hashes and authoritative rows before any production cutover.

## Remaining launch blockers

Until current-week HUMAN prose for all expected games passes live verified-source support, all focused and slate-wide editorial gates pass, and production/Sheet parity is verified, **LAUNCH BLOCKER** is the only defensible status. A green unit-test suite by itself cannot override this.
