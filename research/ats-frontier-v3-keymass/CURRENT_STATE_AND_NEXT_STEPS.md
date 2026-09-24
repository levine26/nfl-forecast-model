# Current State and Next Steps

Phase 1 freezes the V3 hypothesis, training algorithm, T-120 market contract, prediction schema, evaluation rules, stopping rules, numerical core, outcome firewall, hashes, and CI tests.

Phase 2 may begin only after Phase-1 exact-head CI and merge closeout. The first Phase-2 action is to run `fit_frozen_parameters.py` once on 2010–2025 regular-season development rows, persist and hash `frozen_parameters.json`, then generate shadow predictions for eligible post-freeze T-120 games. That fit is development parameter estimation, not historical confirmation.

No outcome scoring, retuning, production writes, ATS selection, or retrospective 2026 use is authorized.