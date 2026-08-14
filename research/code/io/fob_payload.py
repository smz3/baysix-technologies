"""Task 229 (Lever 2) — FOB payload data-plane split.

Principle (spec docs/specs/2026-07-03_fob_payload_dataplane_split.md):
    research.db holds CONCLUSIONS (fob_run_stats), never the raw storyline.

The three raw lifecycle tables (fob_cycles / fob_zones / fob_events) are a
TRANSIENT ingest-staging area only. After a run is ingested + rolled up, its raw
rows are exported here to one Parquet file per (run, table) under
`research/data/fob_payload/run_<id>/` (gitignored, derivable) and then cleared from the DB
(tester.clear_fob_payload_run) so research.db stays ~a few MB and the viewer opens.

zones/events get a denormalised `setup_tf` column (joined from fob_cycles) at
export so analysis can filter by setup-TF without a join. Read a small frame back
via read_fob_payload(run_id, table, setup_tf=..., cols=[...]) — never dump raw to
context (mirrors arctic_io.py discipline). Fully reversible: the source of truth is
the emit CSV (backed up to G:\\My Drive\\baysix_backups).
"""
from pathlib import Path

import pandas as pd

_REPO = Path(__file__).resolve().parents[3]
PAYLOAD_DIR = _REPO / "research" / "data" / "fob_payload"

# table -> SQL that pulls that run's rows (zones/events denormalise setup_tf from cycles)
_EXPORT_SQL = {
    "cycles": "SELECT * FROM fob_cycles WHERE run_id = ?",
    "zones": (
        "SELECT z.*, c.setup_tf AS setup_tf "
        "FROM fob_zones z LEFT JOIN fob_cycles c ON c.cycle_id = z.cycle_id "
        "WHERE z.run_id = ?"
    ),
    "events": (
        "SELECT e.*, c.setup_tf AS setup_tf "
        "FROM fob_events e LEFT JOIN fob_cycles c ON c.cycle_id = e.cycle_id "
        "WHERE e.run_id = ?"
    ),
}
TABLES = tuple(_EXPORT_SQL)

# Columns quarantined by task 261. Reading one is a bug, so raise loudly rather than hand
# back a NULL column that silently collapses a screen to n=0. {table: {col: why}}
_QUARANTINED = {
    "zones": {
        "mfe_r": "producer had no fill gate — 95% of rows were unfilled or insta-stopped. "
                 "NULL in the payload; task 202 rebuilds it.",
        "mae_r": "producer had no fill gate — 95% of rows were unfilled or insta-stopped. "
                 "NULL in the payload; task 202 rebuilds it.",
        "confirm_time": "renamed to next_cf_time (it is a forward pointer, not a fill time).",
        "confirm_price": "renamed to next_cf_price.",
    },
}


def _check_quarantine(table: str, cols) -> None:
    q = _QUARANTINED.get(table, {})
    hit = [c for c in (cols or ()) if c in q]
    if hit:
        why = "\n".join(f"  - {c}: {q[c]}" for c in hit)
        raise ValueError(
            f"quarantined column(s) requested from fob payload {table!r} (task 261):\n{why}")


def run_dir(run_id: int) -> Path:
    return PAYLOAD_DIR / f"run_{run_id}"


def parquet_path(run_id: int, table: str) -> Path:
    if table not in _EXPORT_SQL:
        raise ValueError(f"unknown fob payload table {table!r}; expected one of {TABLES}")
    return run_dir(run_id) / f"{table}.parquet"


def export_run(run_id: int, db_path=None) -> dict:
    """Read run_id's raw rows from the 3 DB tables and write one Parquet file per
    table under data/fob_payload/run_<id>/. Returns {table: n_rows}. Read-only on
    the DB (SELECT) — clearing the rows is a separate code-layer call
    (tester.clear_fob_payload_run) done only after this succeeds."""
    import sqlite3

    from research.code.io import tester
    db_path = str(db_path or tester.DB_PATH)

    dest = run_dir(run_id)
    dest.mkdir(parents=True, exist_ok=True)

    counts = {}
    conn = sqlite3.connect(db_path)
    try:
        for table, sql in _EXPORT_SQL.items():
            df = pd.read_sql_query(sql, conn, params=(run_id,))
            df.to_parquet(parquet_path(run_id, table), index=False)
            counts[table] = len(df)
    finally:
        conn.close()
    return counts


def read_fob_payload(run_id: int, table: str, setup_tf=None, cols=None) -> pd.DataFrame:
    """Pull a run's raw payload frame back from Parquet. `setup_tf` filters to one
    setup-TF (cycles/zones/events all carry the column); `cols` selects columns
    (predicate/projection pushdown). Small frames only — do not dump to context.

    Raises if `cols` names a column quarantined by task 261 (see _QUARANTINED)."""
    _check_quarantine(table, cols)
    path = parquet_path(run_id, table)
    if not path.exists():
        raise FileNotFoundError(
            f"no Parquet for run {run_id} table {table!r} at {path} — re-export via "
            "fob_payload.export_run(run_id) (or re-ingest the emit CSV)."
        )
    read_cols = None
    if cols is not None:
        read_cols = list(dict.fromkeys([*cols, *(["setup_tf"] if setup_tf is not None else [])]))
    df = pd.read_parquet(path, columns=read_cols)
    if setup_tf is not None:
        df = df[df["setup_tf"] == setup_tf]
        if cols is not None and "setup_tf" not in cols:
            df = df.drop(columns=["setup_tf"])
    return df.reset_index(drop=True)


def available_runs() -> list:
    """run_ids that have a Parquet payload on disk (all 3 tables present)."""
    if not PAYLOAD_DIR.exists():
        return []
    out = []
    for d in sorted(PAYLOAD_DIR.glob("run_*")):
        try:
            rid = int(d.name.split("_", 1)[1])
        except ValueError:
            continue
        if all((d / f"{t}.parquet").exists() for t in TABLES):
            out.append(rid)
    return out
