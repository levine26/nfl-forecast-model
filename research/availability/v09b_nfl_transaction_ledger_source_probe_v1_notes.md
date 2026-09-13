# V09B NFL transaction-ledger source probe V1

This branch tests only the first-party NFL.com historical transaction ledger as a possible future chronology source.

It does **not** classify transaction text into roster-state transitions, order same-day transactions relative to kickoff, reconcile weekly roster snapshots, assign game-day eligibility, resolve player identity, construct training labels, or authorize V09B fitting.

The frozen empirical probe covers September in 2017, 2018, 2019, 2020, and 2021 across all six NFL.com transaction categories: trades, signings, reserve-list, waivers, terminations, and other. Cursor pagination must remain inside the same year/month/category endpoint and every fetched page is content-hashed.

If the source class passes, the next research layer is an immutable full-ledger capture for 2017-2021. A separate state-transition taxonomy and same-day chronology audit must qualify before ledger rows can modify a roster state.
