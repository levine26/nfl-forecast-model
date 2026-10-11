# Sunday Signal: approved UI/UX implementation (October 11, 2026)

## Authorized decisions

- **U1 APPROVED:** One visible Top Signals section on the current slate. Remove duplicate mounts; don't erase historical data.
- **U2 APPROVED:** Rank upcoming games first under a visible `Next Up` sort; retain kickoff and all-slate controls.
- **U3 APPROVED:** Label frozen straight-up probability, independent ATS margin preference and validated betting value separately. A nonzero margin difference is **not** a proven wager.
- **U4 APPROVED:** Render differences of win probabilities in **percentage points (pp)** and label the probability-derived spread as `PROBABILITY-IMPLIED LINE`, not an independently modeled ATS margin.
- **U5 APPROVED:** Mobile card prioritization, larger metric type at narrow widths, and progressive detail behind game navigation.
- **U7 APPROVED:** History/Performance Lab, showing the existing 2026 published scoreboard and paired LevLine/market Brier alongside explicit comparability and timeliness caveats. The published scoreboard is *not* an on-time-only cohort; add that cohort only when separately audited.
- **U8 APPROVED:** Keep movement visualizations and clarify that displayed market movement represents no-vig win-probability change, not sportsbook spread movement or causation by context.
- **U9 APPROVED:** Deduplicate concurrent network requests for identical published files without retaining stale data across future fetches. More invasive component unification is a follow-on refactor requiring its own validation.
- **U6 REJECTED:** Do not add a lock-integrity panel. **Preserve existing essential lock-missing/error notices**, immutable receipts and existing lifecycle badges.
- **U10 REJECTED:** Do not add a Kalshi-focused comparison view.

## Scope, rollout and scientific firewall

This change set is a product/presentation patch. It is not authority to alter `F-ST-01-FROZEN-2026`, prediction outputs, pricing signals, scheduled locks, provider credentials, ATS official pick fields, or historical receipts.

**Stage A — first tested release:** U1 duplicate removal, U2 upcoming-first sort, U3 ATS distinction, U4 percentage-point and implied-line semantics, U5 mobile readability, U7 performance summary, U8 chronology labeling, U9 in-flight request deduplication. Require responsive tests and build to pass before merge.

**Stage B — follow-up after validated Stage A:** Full app-state consolidation, route-based chunking/lazy historical data loading, reduced DOM portal mutation, fully audited paired scorecards with on-time and missing-lock cohorts, and new timestamp-qualified sportsbook line-movement charts. Stage B remains within already approved U5/U7/U8/U9 and must not assume unavailable data exist.

**Stage C — separate research/data pipeline:** Qualify NFL injuries, price histories, weather and any other prospective data under their own scientific provenance and cost constraints. Do not add the rejected Kalshi product view. No challenger or model promotion without separate governance.

## Acceptance criteria

1. A single visible featured-signal region and no redundant mounted top-signal portal.
2. Published list is scannable at 320px, 390px, 768px and desktop widths; upcoming selection can be reached without reloading.
3. `pp` appears on winner-probability differences, `points` on margin/spread gaps; probability-implied line does not represent ATS expected margin.
4. UI states no verified positive EV from an ATS model/market margin disagreement alone.
5. Performance data come from published immutable-scoring artifacts, and display no misleading on-time-only comparison or backtested ROI claim.
6. Zero model, lock, market capture, betting strategy or scheduled workflow changes.
7. Existing required browser/responsive and production integrity checks pass; live deployment is verified before the release is called complete.
