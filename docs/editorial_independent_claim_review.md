# Sunday Signal: independent HUMAN claim approval

**Status:** fail-closed production engineering prerequisite, NOT independent factual verification or launch approval.

## Required external reviewer

The existing structural editorial acceptance gate is not enough: its JSON booleans do not authenticate independent review. All three HUMAN production publishers additionally require a complete, provenance-bound HMAC-SHA256 dossier signed with a trusted independent review key. The new signer must be separate from Groq, ChatGPT and candidate publishing; no current reviewer service, signing key or factual approval is presumed.

Configure a secure GitHub Actions secret named SUNDAY_SIGNAL_REVIEW_KEY only after establishing independently controlled reviewer infrastructure. The key must contain at least 32 UTF-8 bytes and must never be committed or passed to the generating model. Dossier location: inputs/sunday_signal/independent_claim_approvals.json. No dossier or key means no HUMAN publication.

Top-level dossier structure: {"payload": {...}, "signature": "lowercase HMAC SHA-256 hex"}. Serialize payload using Python json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) and HMAC-SHA256 with the reviewer secret.

Payload schema_version is 1; canonical_slate_sha256 is the SHA-256 of outputs/this_week.csv raw bytes; games is an exact mapping of every canonical current game ID.

Each game's record requires:
- official_forecast_sha256: SHA-256 of canonical compact sorted JSON of the current CSV row.
- human_paragraph_sha256: SHA-256 of exact first public matchup Read paragraph.
- reviewer_id and timestamp reviewed_utc.
- all_material_factual_clauses_reviewed, independent_semantic_review_complete and point_in_time_evidence_review_complete explicitly true.
- sources: at least two independent publisher families with canonical HTTPS URLs, actual article-content SHA-256, original_article_content_reviewed true, publication and independently archived capture timestamps **before kickoff**.
- claims: comprehensive independently enumerated factual subclaims; every material statement has judgment verified, exact substantive supporting excerpt, matching article-content SHA-256 and independently_entails_claim true.

The gate checks the authenticated attestation, exact byte/snapshot freshness, timestamps, source identity, publisher diversity and per-claim fields. **It does NOT itself prove claim truth, article excerpt presence or reviewer independence.** Those must be established by the trusted external review process. Never fabricate attestations or treat HMAC as a semantic judge.

## Operational handling

With no approved evidence, signing key, or exact dossier, the gate fails closed; public numerics remain usable but factual HUMAN Reads must be withheld. A new forecast row, human paragraph or slate requires a new approval; stale approvals cannot be reused. Missing pre-kickoff original-article captures cannot be manufactured after the game.

Offline regression: python -m pytest -q tests/test_editorial_signed_acceptance.py tests/test_verified_human_source_gate.py.

Keep frozen F-ST official probabilities, past locks, past results and official model governance untouched. Recover by preserving last-good accepted editorial data, not by flipping status flags. After an audit failure, repair sources or claims, independently review, re-sign exact bytes, test, then publish. Key compromise requires key rotation and review of previously approved releases.

**Remaining launch blockers:** This PR neither supplies a reviewer or credential nor verifies any of the 15 Week 5 claim sets. The finalizer still records the existing evidence and claim acceptance fields as false. Launch stays blocked until those substantive prerequisites are satisfied.
