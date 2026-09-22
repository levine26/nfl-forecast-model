# Candidate 4 — Prospective source qualification plan

Status: **pre-outcome / research only**  
Candidate: `ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1`

## Market source gate

Primary candidate source to qualify: **PropLine live NFL game-lines API**.

Public-documentation facts used only to design the audit:
- `GET /v1/sports/football_nfl/odds?markets=h2h,spreads,totals`;
- event/bookmaker/market/outcome structure is documented as compatible with The Odds API conventions;
- per-book `last_update` is exposed;
- free tier is documented as 1,000 requests/day.

Qualification requires live evidence from the repository collector, not the website claim.

A source attempt qualifies a Candidate 4 horizon only if:
1. request timestamp <= nominal horizon cutoff;
2. request timestamp < kickoff;
3. event teams and kickoff resolve uniquely;
4. >=5 sportsbooks supply a valid two-way h2h market;
5. each counted book has a parseable update timestamp <= request timestamp;
6. at least 5 counted books have freshness <=30 minutes;
7. two-way prices are finite and non-zero;
8. no duplicate book key appears in the selected request;
9. normalized no-vig probabilities are in (0,1);
10. raw provider name, request time, event id, per-book names/update times and source count are preserved;
11. no game result, score or post-kickoff field is loaded by the qualification process.

For the T-120 -> T-60 path:
- >=5 identical sportsbooks must exist at both horizons;
- only same-book pairs are used;
- later rows never backfill an earlier horizon;
- T-45/T-30 cannot repair a missing T-60.

If PropLine is unavailable, Candidate 4 fails closed. No other provider is automatically substituted without an explicit source-contract amendment committed before the affected lock.

## Football source gate

Primary V1 football event: **newly known QB unavailability / starter replacement**.

Required pre-T-120 identity state:
- nflverse 2025+ depth-chart row with `dt <= T-120`;
- team, player_name, GSIS id, QB position and rank-1 state;
- unambiguous QB1 only.

Required T-60 shock evidence:
- official NFL inactive article captured before/equal T-60;
- cohort parser V2 semantics pass;
- inactive QB rendered team/name exactly resolves to the frozen T-120 QB1 identity under a new Week 3+ identity contract;
- emergency-third-QB annotations do not by themselves imply starter loss.

Direction:
- home QB1 newly inactive => `S_QB=-1`;
- away QB1 newly inactive => `S_QB=+1`;
- otherwise `S_QB=0`.

No magnitude is assigned. No backup-QB “points”, Elo adjustment, analyst score or LLM probability is permitted.

## First-game rule

The first game can be Candidate 4 eligible only when:
- full Candidate 4 preregistration was committed before its T-120 cutoff;
- the market source passes its outcome-blind qualification on or before the required market state;
- QB identity/source contracts were frozen before the relevant evidence arrived.

If any requirement is late, that game is excluded rather than reconstructed.
