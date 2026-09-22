# Props 2.1 end-to-end deployment acceptance

Status: VERIFIED for the frozen September 20 prospective publication.

## Backend publication

- Live workflow run: 35477049179
- Trigger SHA: e851c4ae703bd7fd2d34c052190a6a546925f3a2
- Generation base SHA: f409616b5583c7d1338cb5d3cdfaf0a95021ef7e
- Published commit: ba723255982c79ffe6072c714dd0ee2c37e1fa34
- Props 2.1 receipts: 3,439 across 15 games
- Provider/mode: PropLine / configured
- Pregame chronology: PASS
- Protected-system mutation: none

## Committed evidence

The publication commit contains all three required Props 2.1 surfaces:

- challenger_outputs/props21/public_challenger.json
- challenger_outputs/props21/forecast_originals.jsonl
- challenger_outputs/props21/live_slate_audit.md

Their Git blob SHAs are frozen in POST_SUNDAY_EVIDENCE_MANIFEST.json.

## Sunday Signal deployment

The live publish explicitly dispatched dashboard workflow run 35477618922 from the exact publication commit ba723255982c79ffe6072c714dd0ee2c37e1fa34.

The dashboard run completed successfully. Its build job passed the dedicated "Publish the separate Props 2.1 Challenger surface" copy step, the dashboard build, and the Pages artifact upload. Its deploy job then completed the GitHub Pages deployment successfully.

The deployment workflow copies the committed challenger artifact verbatim from challenger_outputs/props21/public_challenger.json to site/public/data/props21/public_challenger.json before the site build. The challenger route is #/props/challenger.

## Evidence boundary

Later valid live refreshes reduced the current live slate as games started. They are not substitutes for the frozen 15-game prospective experiment. Postgame evaluation must use the receipt ledger at publication commit ba723255982c79ffe6072c714dd0ee2c37e1fa34 and may only join finalized outcomes in a separate evaluation layer.

The NYG-LA game has kickoff 2026-09-22T00:15:00+00:00 and is intentionally left ungraded until final.
