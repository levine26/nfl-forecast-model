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


## Shared-market contract preservation

A second pre-execution correction preserves the previously frozen LevLine 4 market semantics while satisfying Candidate 4's stricter source rule:

- the shared legacy market qualification constant remains **2 books**, exactly as frozen for existing LevLine 4 horizon research;
- Candidate 4's scheduled collector retry threshold is separately set to **5 books**;
- therefore a two-book consensus remains valid for the older LevLine 4 research candidate, but it does **not** stop Candidate 4 collection retries;
- Candidate 4 itself reconstructs its horizon state only from at least five fresh, same-provider book rows and still requires at least five common books across T-120 and T-60.

This avoids retroactively changing another research program merely to satisfy Candidate 4. It changes no Candidate 4 threshold and uses no completed Candidate 4 outcome.
