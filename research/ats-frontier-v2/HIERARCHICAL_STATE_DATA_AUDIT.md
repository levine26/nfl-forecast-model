# HIERARCHICAL STATE DATA AUDIT

## M3 status

`DATA_QUALIFIED` for the **core chronology-safe hierarchical state**.

nflverse play-by-play is available back to 1999 and provides sufficient prior-game information to construct lagged offense/defense/QB process inputs. The future model must materialize target-game rows only from games completed before the target prediction timestamp.

Eligible core inputs include lagged EPA, pass EPA, rush EPA, success rate, explosive rate, neutral-state metrics, pace, PROE, QB prior-game performance and team scoring state, subject to field-level chronology checks.

## Chronology contract

- target game's PBP must be absent;
- only prior-game records are eligible;
- publication/stat-correction lag must be frozen in Phase 3 where the exact operational horizon matters;
- season transitions must be explicit rather than silently concatenated;
- canonical team identity must normalize relocations/abbreviation changes;
- coaching/QB regime features, if used, require timestamped regime boundaries.

## Personnel boundary

Rich current-week unit/personnel state is **not** implied by M3 qualification. Any current player availability, starter, role or depth input inherits M2's PIT restrictions.

## No fitting

No hierarchical model, state-space model or hyperparameter grid was fit or selected in Phase 2.