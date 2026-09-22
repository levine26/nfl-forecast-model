# Props Reset Manifest

Reset boundary commit: `f38c1445fcad04e7c8c2ec49b7423f4d232739a8`  
Full preservation branch: `archive/props-pre-revamp-2026-09-21`

The active branch intentionally removes the old player-prop implementation while preserving its history.

Removed categories:

- Props production/live orchestration;
- Props GitHub Actions workflows;
- Props 2.0/2.1/2.2 research code and contracts;
- Props simulation, opportunity, efficiency, player-state, market, publication and QA modules;
- Props-specific scripts and tests;
- Props UI routes/components/styles/tests;
- Props raw publication outputs and challenger ledgers;
- Props preregistered live priors tied only to the retired implementation.

Modified shared surfaces:

- dashboard workflow: no Props build/publication steps or Props path triggers;
- app entrypoint: no Props route and no hidden Props component mount;
- active handoff: Props marked retired and redirected to the archive record.

The full old tree remains reachable through the preservation branch above.
