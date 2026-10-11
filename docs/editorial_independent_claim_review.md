# Sunday Signal: independent HUMAN claim acceptance

**Operational state:** This safeguard is a fail-closed verification prerequisite. It is not a source-review service, evidence archive, semantic fact checker or launch authorization.

## Separation of duties

The authoring providers (Groq, ChatGPT and candidate publishers) do not approve their own factual assertions. A separately controlled reviewer must inspect original publisher articles, point-in-time captures and every substantive football clause. Only that reviewer holds the **Ed25519 private signing key**. Production workflows receive the **Ed25519 public verification key only**, as the GitHub Actions repository variable `SUNDAY_SIGNAL_REVIEW_PUBLIC_KEY` (PEM SubjectPublicKeyInfo). They cannot use that public key to fabricate a signature.

The signed review dossier path is `inputs/sunday_signal/independent_claim_approvals.json`. No trusted reviewer, public key or valid exact-slate dossier means no new HUMAN Read can publish. Never commit a private signing key or provide one to generation providers.

## Dossier contract

A JSON object with exactly two top-level keys: `payload` and `signature`. The signature is the standard base64 encoding of the 64-byte Ed25519 signature over the UTF-8 bytes of `json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)`.

The `payload` schema must contain:

- `schema_version: 1`, SHA-256 of the exact bytes of canonical `outputs/this_week.csv`, and a game map covering every current canonical game ID exactly once.
- For each game: SHA-256 of the canonical JSON representation of the CSV prediction row, SHA-256 of the exact published first HUMAN paragraph, independent `reviewer_id`, timezone-aware `reviewed_utc`, and positive attestations of complete factual-clause review, independent semantic review and point-in-time verification.
- At least two independent publisher source receipts, with canonical HTTPS URLs **identical to the article URLs publicly cited in the same Read**, article-content SHA-256, independent original-article review, publication time and verifiable archive capture time both preceding kickoff.
- Every independently enumerated factual subclaim, exact statement, `judgment: "verified"`, substantive verbatim supporting excerpt, article fingerprint linking that claim to reviewed source bytes, and `independently_entails_claim: true`.

This gate verifies signer authenticity, full-slate identity, citation-to-receipt linkage, per-game hash consistency, timeframe, source-family diversity and explicit proof fields. It cannot independently establish semantic entailment, completeness of factual-clause extraction, excerpt presence in archived body text or reviewer authorization. Those remain the responsibility of the independent reviewing service and evidence archive. False affirmations by a reviewer do not become true merely because the signature verifies.

## Release, recovery and rollback

With missing public verification key, absent dossier, invalid signature, stale official prediction bytes, changed Read text, unreviewed cited source, post-kickoff capture or unverified claim, fail closed without publishing HUMAN content. Keep accurate official numerical forecasts visible with appropriate degraded editorial status. Re-run external evidence capture, independent claim review, and signing for the exact current slate rather than changing flags.

Focused offline regression command:

`python -m pytest -q tests/test_editorial_signed_acceptance.py tests/test_verified_human_source_gate.py`

Rollback is editorial-only. Preserve last-good independently accepted text when snapshot-compatible, never substitute stale editorial content under newer forecast numbers, and never rewrite F-ST, historical locks, grades or research candidates. If the private signing key is compromised, revoke the corresponding public key and require genuinely new reviews under a new signing identity.

**Known launch blockers:** no independently authorized review service, signing arrangement, complete timestamped original-article evidence archive or accepted claim inventory is connected. The current Week 5 acceptance audit remains unverified. This engineering change makes mispublication harder; it does not fix the underlying football writing quality by itself.
