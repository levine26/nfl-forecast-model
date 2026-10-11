# Sunday Signal — live source-acquisition diagnostic (shadow)

The Week 5 ChatGPT fallback candidate slate previously passed legacy focused and full-slate URL-shape/prose validation while several cited sources were generic viewing guides, betting previews, or league-wide picks. The production acceptance audit still records `article_resolution_verified=false` and `claim_support_verified=false`. Neither a plausible URL nor a successful LLM request establishes article provenance.

## Purpose and interface

`scripts/editorial_live_evidence_sweep.py` implements a **non-production** complete-slate audit. It reads canonical game IDs/team identities from `outputs/this_week.csv`, candidate source title and URL from `inputs/chatgpt_media/fallback/<game_id>.json`, and fetches every candidate article using `nfl_forecast.editorial_article_capture.capture_report`. The latter insists on approved original publisher HTTPS, no unapproved redirect, actual matching article headline, meaningful non-navigational content, and bounded downloaded bytes. A content hash, text hash, original title, retrieval timestamp, independent publisher family and relevant teams are included in the report.

All games are processed even when some publishers return errors. The output `research_outputs/editorial/article_provenance_sweep.json` (or `--output` override) summarizes candidate resolution, provenance errors and cross-source team coverage. The original article bodies **are not persisted** in this report. It is schema-versioned with a canonical forecast-input checksum and a frozen “publication authorized: false” field. It never writes official forecasts, locks, history, public site Reads or Sheet cells.

Example: `PYTHONPATH="$PWD/src:$PWD" python scripts/editorial_live_evidence_sweep.py --output /tmp/editorial-article-provenance.json`.

## Reliability and limitations

* Every citation is evaluated independently. Wrong-team, bogus-title, navigation, 404, blocked publisher and transport/size issues are game-scoped errors; a single rejection does not terminate the sweep.
* Independent original publisher families must collectively mention both canonical teams. This is a necessary but not sufficient editorial test.
* A quoted sentence appearing on a retrieved publisher page does **not** prove a generated football claim is true; roster verification, semantic claim entailment, proper dates and actual sources remain the responsibility of the separate trusted reviewer and `editorial_source_receipts_shadow`.
* Results can be incomplete because publisher defenses deny automated HTTP acquisition. Such a refusal is reported, never silently upgraded to verified.
* GitHub Actions runs synthetic safety tests on pull requests. On a merge of this script/workflow to main, a one-time live shadow sweep attempts all current sources and uploads its report as an Action artifact. Manual workflow dispatch is also supported.
* Running the sweep does **not** switch editorial authorities or authorize publishing. A future separate promotion must enforce a trusted claim-level validation receipt, roster reconciliation, full-slate uniqueness, deterministic paragraph 2, lock integrity, canonical SHA compare-and-swap, and production rollback.

### Governance

No modifications to `F-ST-01-FROZEN-2026`, the official probability strategy, data features, historical predictions, pick locks, grading, or challenger research. This tooling is intentionally downstream and read-only.
