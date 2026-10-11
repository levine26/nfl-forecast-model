# Article-content evidence capture — non-production

**Status:** Independent shadow-layer component, not publication authority.

Previous editorial validation accepted URL-shaped source references without proving that the page resolves, contains the cited article, covers the actual matchup or supports the asserted claim. This component creates reviewable **source-content receipts** from approved original-publisher HTML and explicitly distinguishes that level of proof from fact/claim entailment.

`capture_report(url, expected_title, away_name, home_name)` fetches a direct HTTPS reporting article with redirects disabled, 9-second timeout and 1MB body cap. It rejects non-200 pages, non-HTML content, generic viewing/betting/navigation titles, claimed titles contradicted by the actual H1, thin pages, and wrong-matchup content. It records publisher family, article title, original bytes SHA, extracted article text SHA, retrieval timestamp, raw published timestamp if present, and team coverage. `locate_quote` requires a literal excerpt from retrieved content and returns a quote checksum. `require_independent_publishers` requires two distinct publisher-family content receipts, not just URL strings.

Critically: **quote present** is not the same as **claim entailed**, and a club/press account may be incomplete or mistaken. This module always returns `claim_entailment_verified=false`; an independent trusted claim and roster verifier must assess the material factual assertions before the article can participate in a production HUMAN-Read acceptance receipt. No publisher credential, claimed URL, or self-asserted LLM source citation may set the trusted validation flag.

In this slice, the module is *not wired* into the production writer or the source-fetch loop. The purpose is to test the evidence-acquisition boundary in isolation, protect against fabricated URLs, deceptive titles, wrong-team material and missing original content, and establish a stable receipt schema for the game-scoped shadow ledger.

## Remaining integration gates

1. Connect to existing current-matchup news discovery via bounded origin fetch, with source outages reported per game.
2. Add reputable original-publisher evidence snapshots, factual claim extraction, verified roster/transactions, and independent claim-support receipts.
3. Replay complete Week 5 evidence with two independent direct articles per game and fail-closed, structured diagnostics for every article/source failure.
4. Bind the trusted verifier's acceptance receipt to the immutable game-scoped shadow ledger and deterministic numeric renderer; no cutover until verified.
5. Retire legacy URL-only acceptance after equivalent/new quality is demonstrated.

**Scope:** no edits to F-ST-01-FROZEN-2026, features, probabilities, history, locks, grading, challengers, or public website.


## Consolidated verification pipeline (October 10 repair)

The **sole evidence-verification authority in shadow** is `editorial_source_receipts_shadow.verify_retrieved_article` from PR #674. This module is its limited HTTP acquisition adapter, **not** an independent second acceptance engine. Use `capture_and_verify_source(game_id, url, expected_title, team_aliases, claims)` to fetch one approved original article and submit actual extracted content to that verifier. The resulting receipt proves URL/title/body identity and quote presence only; semantic football claim entailment, roster verification and final HUMAN editorial approval remain separate and are not asserted.

Downloads use streamed, redirect-disabled HTTPS requests with a total one-megabyte byte cap; responses are always closed. An article about one team can supply part of the evidence packet, but the final packet must cover both teams through **two independent publisher families** using `require_independent_publishers(..., expected_teams=...)` and ultimately `audit_matchup_receipts` from the sole verifier.

No production writer or canonical numerical file imports this acquisition module. It must remain in shadow until a trusted factual-claim reviewer and full-slate publisher have been independently validated.
