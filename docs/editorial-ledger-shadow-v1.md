# Editorial authority refactor — shadow ledger v1

**Status: NON-PRODUCTION.** This is the first independently testable component of the selected major editorial refactor. No production workflow reads this ledger and no writer publishes from it.

## What this implements

- **One authoritative game record** keyed by a stable season/week/away/home game ID, with append-only accepted revisions. A rejected replacement never changes the most recent accepted revision.
- **Idempotence and optimistic concurrency** through candidate fingerprints and expected revision checks. Local JSON writes use `fcntl` file locks, same-directory staging, fsync, atomic rename, and digest-based compare-and-swap. Cross-host GitHub Actions still requires remote ref CAS before a production migration.
- **Receipt attachment:** a candidate includes two publisher-family source receipts with retrieved time, content fingerprints and claims; a *separate, trusted* validation receipt must reference the exact candidate SHA and assert both article/claim and editorial acceptance. This module checks integrity and structure only. It does **not** retrieve articles or fact-check them, and the candidate must never be allowed to mint its own validator receipt.
- **Context-update isolation:** injury and contextual updates can mark content `review_required` without modifying accepted prose. An actual factual contradiction retains the history but prevents a release until cleared.
- **Release staging:** a shadow release index only points at complete, accepted editorial revisions and the provided immutable canonical forecast fingerprint. The existing production canonical renderer remains responsible for all numerical explanation fields.

## Non-goals and boundaries

This does not solve the Groq quota, provide a headless ChatGPT API, resolve/report two independent articles, validate live claims, perform the full-slate prose test, or deploy a new site. The public site and outputs continue using their current pipeline. These missing capabilities are **launch blockers**, not silently treated as completed features.

The `passed` flags here are **trusted caller inputs**, not proof that sources resolve. Before promotion, connect the actual verified-source fetch and comprehensive focused/full-slate validators, plus signed or otherwise independently protected validation receipts. Add a GitHub remote-ref compare-and-swap single-publisher path, bootstrapping from current accepted provider records only if they can be independently revalidated.

## Acceptance tests for this isolated stage

`pytest -q tests/test_editorial_ledger_shadow.py` checks versioning, idempotence, stale revisions, numerical-field firewall, independent source receipt structure, source/validator mismatch, accepted content surviving freshness review, contradiction blocking release, full-slate fail-closed behavior, atomic interrupted writes, and tampering detection. The new PR-only workflow runs these without production write permissions.

## Next migration gates

1. Implement verified live article fetch/content/claim receipts. Current URL-shape source checks are insufficient.
2. Connect trusted validators to the per-game ledger in **shadow**, replay all 15 Week 5 inputs, and produce structured rejection diagnostics.
3. Validate deterministic paragraph-2 regeneration separately against canonical live/pre-lock and immutable locked forecasts.
4. Introduce a single guarded editorial publisher using a GitHub main-ref lease; test provider outage and concurrent workers, then exercise rollback.
5. Run the shadow and incumbent in parallel for controlled comparison, cut over after CI and production acceptance, and retire legacy manifest-centered publication writers.

No protected F-ST artifact, probability strategy, diagnostic margin, official lock, historical grading record, or challenger research code changes are permitted in this migration.
