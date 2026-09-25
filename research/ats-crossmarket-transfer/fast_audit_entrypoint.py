from __future__ import annotations

"""Fast audit entrypoint for ATS cross-market transfer V1.

The audit logic is unchanged. This wrapper replaces only expensive historical loading,
center-archive construction, and scalar lattice evaluation with the hard-gated
schedule-only scaffold, exact probability-only archive, and vectorized adaptive-support
implementation already used by the candidate runner. No candidate definition, score,
threshold, grid, chronology rule, or decision rule is changed.
"""

import audit_and_postprocess as audit
import probability_only_entrypoint as probability_entry

# audit_and_postprocess imports its own run_experiment module instance. Replace only
# computationally equivalent helpers. The schedule-only historical scaffold is guarded
# by the accepted #582 game-id hash before it can enter any audit calculation.
audit.xm.hist.build_historical_games = probability_entry.build_schedule_only_historical_games
audit.xm.hist.build_center_archive = probability_entry.build_probability_archive
audit.xm._adaptive_support = probability_entry.fast_adaptive_support

if __name__ == "__main__":
    audit.main()
