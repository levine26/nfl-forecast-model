# Prospective Prediction Contract

Every eligible future game must be serialized before kickoff and before outcome access. Identity is `(candidate_id, game_id, T-120m)` and is append-only; duplicates are rejected.

Required immutable fields include game ID, season/week, kickoff, prediction timestamp, provider, horizon target, request and maximum quote timestamps, provider event ID, source-book count/names, raw home spread, canonical home margin, available side prices, full analytic-unbounded candidate PMF descriptor, full analytic-unbounded null PMF descriptor, candidate/null cover-push-loss probabilities, raw-input SHA256, model-code SHA256, config SHA256, and prediction SHA256.

A PMF descriptor is the canonical full unbounded parametric PMF representation—family, location, scale, df, key offsets, analytic normalizer—not a clipped finite grid. Outcome/result fields are rejected by the Phase-2 serializer.