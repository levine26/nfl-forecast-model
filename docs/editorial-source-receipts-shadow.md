# Editorial evidence receipts — shadow-only contract

The existing direct-source URL policy is necessary but insufficient. A URL may resolve to a legitimate first-party football page that says nothing about the claims attributed to it. In a verified live Week 5 check, the Detroit–Arizona candidate cited a Cardinals matchup-notes story plus a Lions how-to-watch guide for a new Marvin Harrison Jr. trade/inactive claim. The fact itself had independent direct reporting, but the candidate's attached articles did not substantiate it. A focused-validator pass therefore **does not equal fact-checking**.

The `src/nfl_forecast/editorial_source_receipts_shadow.py` module introduces a **research-only** source-content boundary. The trusted research/retrieval worker must obtain a real HTTP response, canonical resolved URL, extracted article body, headline, and retrieval timestamp. This module then checks:

* Allowlisted HTTPS direct article identity; no invented/non-report URL or changed final URL.
* HTTP 200 response, exact normalized published title, substantive extracted body.
* Explicit rejection of generic viewing guides, betting/fantasy filler, and schedule pages.
* Matchup team relevance grounded in canonical team aliases supplied by the caller; two independent publisher families covering both opponents in aggregate.
* Source body SHA-256, retrieval time and available publication time.
* For each claimed fact, a substantive quoted supporting passage that actually occurs in the retrieved body; immutable content fingerprints.
* Structured rejection categories with a fail-closed default.

**Security and truth limitations:** The verifier does **not** itself perform network fetching or attest that the supplied `fetched` object originated from the target website. It must be called only by a trusted acquisition worker, never with untrusted LLM-provided fake HTTP metadata. Quoted text presence does not prove that the quote semantically entails the generated statement. Every output sets `semantic_claim_entailment_verified=False`; the packet explicitly sets `editorial_publication_authorized=False`. Trusted semantic/factual review, roster/transaction corroboration, article freshness and the existing editorial/full-slate gates remain required before a HUMAN Read can be published. There is no connection to production workflows or outputs.

This feature neither edits numerical forecasts, F-ST model/strategy, market calculations, scores, immutable official locks, nor grades. It does not create a second editorial ledger: accepted human state is owned by the existing shadow `src/nfl_forecast/editorial_ledger_shadow.py` introduced in PR #667.

Run `pytest -q tests/test_editorial_source_receipts_shadow.py`.

Required future integration: trusted network acquisition and content extraction, semantic claim reviewer, approved current-roster evidence, candidate-bound receipt generation compatible with the existing ledger, end-to-end Week 5 real-source replay, then controlled production cutover with rollback. Until then **LAUNCH BLOCKER**.
