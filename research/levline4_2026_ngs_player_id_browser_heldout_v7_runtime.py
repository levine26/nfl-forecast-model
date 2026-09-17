from __future__ import annotations

"""Execution-safe V7 entrypoint for the preregistered resolver.

The first V7 implementation used JSON-style ``true``/``false`` identifiers in
receipt construction. Python parses those identifiers but would raise NameError
only after the browser experiment. This pre-empirical wrapper binds those names
to the intended Python booleans without changing any contract, resolver,
selection, query, gate, threshold, or authority semantics.
"""

from research import levline4_2026_ngs_player_id_browser_heldout_v7 as impl

# Pre-empirical implementation defect repair only.  The underlying V7 module
# resolves these globals at runtime when constructing the receipt.
impl.false = False
impl.true = True

canonical_query_name = impl.canonical_query_name
source_name_keys = impl.source_name_keys
query_plan = impl.query_plan
select_targets = impl.select_targets
resolve_target = impl.resolve_target
evaluate_gates = impl.evaluate_gates
run_probe = impl.run_probe


def main() -> int:
    return impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
