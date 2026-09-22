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
