from __future__ import annotations

"""CLI compatibility shim for the single central production Read publication gate."""

from nfl_forecast.read_publication import (  # noqa: F401
    ReadSyncError,
    _csv_rows,
    _factor,
    _near,
    _preserved_context,
    main,
    synchronize_file,
    synchronize_reads,
)

if __name__ == "__main__":
    raise SystemExit(main())
