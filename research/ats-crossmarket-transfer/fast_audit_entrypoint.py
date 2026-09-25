from __future__ import annotations

"""Fast audit entrypoint for ATS cross-market transfer V1.

The audit logic is unchanged. This wrapper replaces only the expensive historical
center-archive construction and scalar lattice loop with the probability-only archive
and vectorized adaptive-support implementation already used by the candidate runner.
No candidate definition, score, threshold, or decision rule is changed.
"""

import audit_and_postprocess as audit
import probability_only_entrypoint as probability_entry

# audit_and_postprocess imports its own run_experiment module instance. Replace only
# computationally equivalent helpers so preflight/postprocess do not refit unrelated
# fair-margin regressions and do not repeat scalar Student-t cell evaluation.
audit.xm.hist.build_center_archive = probability_entry.build_probability_archive
audit.xm._adaptive_support = probability_entry.fast_adaptive_support

if __name__ == "__main__":
    audit.main()
