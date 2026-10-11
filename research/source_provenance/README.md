# Week 5: live source provenance audit (shadow only)

The existing single-article capture verifier records real HTTPS article retrieval, a
content fingerprint, and body-derived team coverage. However, Week 5 candidates
in `inputs/chatgpt_media/fallback/` only provide source titles and URLs, not
per-claim excerpts, point-in-time attestations, or independent verification that
the football assertions actually follow from the reporting.

`research/source_provenance/audit_human_source_provenance_shadow.py` audits all canonical candidate
games independently. It records article identity, publisher independence,
retrieval timestamps, SHA-256 fingerprints, reported-team coverage, and
per-source errors. No fetched article text is persisted. A failing source does
not abort the rest of the slate. Sources are restricted to pre-approved direct
HTTPS publisher articles; HTTP redirects or generic reporting shells do not
count as successful retrievals.

## Run without publication

```sh
python research/source_provenance/audit_human_source_provenance_shadow.py \
  --manifest inputs/chatgpt_media/fallback/manifest.json \
  --input-dir inputs/chatgpt_media/fallback \
  --output /tmp/sunday_signal_article_provenance_shadow.json
```

Inspect `games[GAME_ID].sources` and `games[GAME_ID].issues` in the JSON
report. The tool **never** updates official forecasts, release artifacts,
editorial draft inputs, the accepted HUMAN ledger, or GitHub Pages content.

Even if all articles resolve, the report **always** sets
`full_slate_claim_support_verified=false` and
`publication_authorized=false`. Cited pages must still be reviewed against
each specific factual/analytical assertion, with attributable literal
excerpts and independent semantic support checks, before a trusted reviewer
may issue the attestation required by production acceptance.

A successful HTTP 200, exact headline, or independent publisher pair is *not*
proof of roster accuracy, injury status, source freshness at kickoff, analytical
truth, or permission to publish a candidate. These checks must never be
promoted into the immutable frozen forecast model.
