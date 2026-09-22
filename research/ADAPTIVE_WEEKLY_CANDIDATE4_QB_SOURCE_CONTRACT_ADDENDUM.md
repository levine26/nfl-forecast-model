# Candidate 4 QB source-contract schema clarification

Status: **PRE-EXECUTION CLARIFICATION — NO SCIENTIFIC RULE CHANGE**  
Date: 2026-09-22  
Parent contract: `ADAPTIVE-CANDIDATE4-QB-SHOCK-SOURCE-V1`  
Candidate preregistration: `74ecd303545c09f57593546472d27438e3d8a204`

Before the first Candidate 4 live execution, the QB evidence record is clarified to preserve **both teams'** T-120 QB1 identities rather than one generic QB1 field.

Required bilateral fields:
- `home_t120_qb1_player_name`
- `home_t120_qb1_gsis_id`
- `home_t120_depth_timestamp_utc`
- `away_t120_qb1_player_name`
- `away_t120_qb1_gsis_id`
- `away_t120_depth_timestamp_utc`

Reason: a qualified zero-shock observation must prove that neither frozen QB1 appeared in the qualified inactive evidence. One generic identity field cannot audit that state.

Unchanged:
- source families;
- T-120/T-60 horizons;
- exact-name/team identity rule;
- no fuzzy matching;
- shock direction;
- no player-value magnitude;
- Candidate 4 switching rule;
- thresholds;
- production firewall;
- completed 2026 outcomes used for design/selection = 0.

This is an evidence-schema clarification only. It does not create a new candidate clock.


## Immutable T-120 execution clarification

Before the first Candidate 4 primary game, the operational source path is further hardened:

- QB1 identity is now **captured and content-hashed during the one-sided T-120 window itself**;
- the T-120 capture accepts only source records already observed by the capture timestamp;
- the T-60 inactive comparison consumes that immutable QB1 snapshot file;
- the T-60 runner does **not** re-query nflverse/nflreadpy depth charts and does not retrospectively derive a T-120 identity from a later data pull;
- if the T-120 snapshot is missing, incomplete, late, ambiguous, or has an identity mismatch, that game fails closed;
- a later depth-chart pull may not repair a missed T-120 snapshot.

This strengthens point-in-time evidence preservation without changing the frozen QB-shock definition, horizons, switch gate, threshold, or player-value authority.
