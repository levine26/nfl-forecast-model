from __future__ import annotations


LEDGER_IDENTITY_COLUMNS = (
    "game_id",
    "horizon",
    "row_type",
    "sportsbook_key",
    "request_timestamp_utc",
)

QUALIFYING_CLOSE_ROW_TYPE = "consensus"
MIN_CONSENSUS_BOOKS = 2


def attempt_identity(row: dict) -> tuple:
    return tuple(row.get(column) for column in LEDGER_IDENTITY_COLUMNS)
