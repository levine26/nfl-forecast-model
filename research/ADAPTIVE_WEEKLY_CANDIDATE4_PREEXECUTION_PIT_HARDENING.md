# Candidate 4 pre-execution PIT hardening note

Date: 2026-09-22  
Candidate: `ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1`  
Frozen preregistration: `74ecd303545c09f57593546472d27438e3d8a204`  
Completed Candidate 4 outcomes used: **0**

## Correction

Before the first eligible Candidate 4 game, the decision constructor was hardened to reject any incumbent F-ST row whose immutable production lock timestamp is **later than nominal T-60**.

The preregistered Candidate 4 decision is made at T-60. Therefore an incumbent created after T-60 did not exist at the decision cutoff and cannot legally seed the challenger.

New fail-closed reason:

`incumbent_lock_after_t60`

## Scientific effect

This is a mechanical point-in-time enforcement correction only.

Unchanged:
- Candidate ID/version;
- T-120 and T-60 market horizons;
- five-common-book requirement;
- market breadth threshold;
- QB shock definition;
- switching rule;
- probability rule;
- controls/ablations;
- inference plan;
- production firewall.

No completed 2026 Candidate 4 result informed this correction. No prospective Candidate 4 decision had been locked before it was made.
