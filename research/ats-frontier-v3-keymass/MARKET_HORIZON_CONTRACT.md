# Market Horizon Contract

Provider: `The Odds API`, region `us`. Horizon: `T-120m` exactly, chosen for existing governed capture reliability rather than historical model performance.

Use the latest capture at or before kickoff-minus-120-minutes and no more than 7.5 minutes early. Never use a request or bookmaker quote timestamp after the target. Require at least two unique books with valid home spread points and timestamps. Consensus raw home spread is the median across valid books. The Odds API raw home handicap uses sportsbook sign; repository canonical expected-home-margin is its negative.

If fewer than two valid books exist, timestamps are missing/late, event identity is unresolved, or T-120 was missed, the game is prospectively ineligible. No later quote substitution or retrospective repair. Side prices may be retained for economic diagnostics when genuinely same-horizon; h2h/total are optional and cannot alter the candidate.