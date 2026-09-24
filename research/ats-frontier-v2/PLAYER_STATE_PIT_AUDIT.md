# PLAYER STATE PIT AUDIT

## Governing rule

Same-game realized participation, snaps, final gamebooks and final inactive state are not pregame state unless an explicit timestamped source proves the information existed by the prediction horizon.

## Component qualification

### Ability
`DATA_QUALIFIED` from lagged prior-game play/snap/advanced information. Same-game data are excluded.

### Participation probability
`PARTIALLY_QUALIFIED`. nflverse's historical injury source ended after the 2024 season. Existing repository research separately qualified a narrow 2025 final-practice-report reconstruction before T-120, with approximately 99.93% resolved player-week coverage within that specific source/scope. That does not authorize a 2022–2025 unified contract.

### Expected role
`PARTIALLY_QUALIFIED`. Lagged usage is valid; current-week role changes require timestamped depth/status evidence. nflverse depth charts changed after 2024: 2025+ updates are timestamped and appended, enabling PIT assignment for the newer era.

### Replacement identity
`PARTIALLY_QUALIFIED`. Requires timestamped roster/depth state. Never infer from eventual same-game snaps.

### Replacement quality
`DATA_QUALIFIED` from historical prior information once replacement identity is legitimately known.

### Announcement timestamp
`REQUIRED`. Any feature whose meaning is information arrival must carry an explicit source timestamp or fail closed.

## Existing repo evidence

- `research/availability/2025_reconstruction_qualification_v1.json` establishes a narrow 2025 final-practice-state T-120 qualification.
- `research/availability/harmonization_regular_season_v2_failure_receipt.json` records a failed-closed 2022–2025 harmonization attempt on identity/semantic gates.
- `research/levline4_pit_personnel_state_v1_contract.json` prohibits back-propagating observations, treating absence as healthy, or adjudicating conflicting sources without evidence.

## M2 conclusion

Broad `FRONTIER-M2-PLAYER-STATE-DELTA` is `PARTIALLY_QUALIFIED`; Phase 3 may use only explicitly qualified subcomponents/eras and must not silently harmonize incompatible historical states.