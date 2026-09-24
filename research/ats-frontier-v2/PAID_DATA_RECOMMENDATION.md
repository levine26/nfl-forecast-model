# PAID DATA RECOMMENDATION

No purchase was made in Phase 2.

## Preferred first purchase if M1 is authorized

**The Odds API — 20K plan, $30/month USD (current public price at evidence cutoff 2026-09-23).**

Why first:
- historical featured-market archive from 2020-06-06;
- NFL moneyline, spreads and totals;
- multi-book structure;
- snapshot timestamp returned at or before requested time;
- 10-minute archive cadence initially, 5-minute cadence from September 2022;
- public docs make the PIT selection semantics unusually explicit.

Historical endpoint cost is 10 credits per region per market, so a request for h2h + spreads + totals in one region costs 30 credits. A 20K-credit month is appropriate for a bounded qualification pull, not necessarily a full every-snapshot multi-season research extraction.

Source: https://the-odds-api.com/

## Alternative

**SportsDataIO Discovery Lab Odds — $99/month or $599/year** for personal/non-commercial real data, according to current public product documentation. Its NFL `GameOdd` schema contains sportsbook identity, Created/Updated timestamps, spread-side payouts, moneylines and totals, and its workflow docs describe all line movement changes. Historical/Vault/commercial access beyond that may require sales terms/quote.

Sources:
- https://sportsdata.io/developers
- https://sportsdata.io/help/data-rights-and-licensing-questions

## Free/prospective alternative

PropLine supplies current/prospective multi-book history, including Pinnacle-related metadata, but its archive starts in April 2026. It cannot replace historical pre-2026 M1 evidence.

## What cannot be completed without historical real-data access

- season × book × horizon coverage percentages;
- exact spread-side-price completeness;
- book identity continuity over the intended training era;
- quote-age and path-density distributions;
- empirical leader/follower reconstruction coverage;
- a final `DATA_QUALIFIED` M1 gate.

Historical timestamped multi-book odds remains the only paid-data category supported by this program at Phase 2.