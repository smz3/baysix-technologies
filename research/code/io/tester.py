"""
G4 (Live) — FIDELITY writers for research.db.

The MT5 Strategy-Tester evidence is NOT a separate database: port-fidelity is
Protocol 4.0's *last gate* (G4 — Live: MT5 tester -> demo -> live parity), so
tester_runs + tester_trades live inside research.db next to step4_results. This
module owns their schema and all writes (CLAUDE.md rule 10), mirroring
pipeline.py conventions (_conn/_now/VALID_* tuples).

Flow:
    ingest_tester_run(...)        -> run_id  (run header + config provenance)
    ingest_tester_trade(run_id, ...) per closed tester round-trip (join key = ticket + entry_ts)
    log_fidelity_diff(run_id, ...) -> writes the diff vs the Python research result,
                                      sets fidelity_verdict, and on 'pass' calls
                                      pipeline.pass_gate(idea_id, 4, ...).

G4 is what execution.register_deployment() / open_deploy_gate('FORWARD') read
before a deployment may touch a broker account.

Spec: docs/reference/execution_schema.md (§research.db — G4 FIDELITY evidence) +
docs/reference/research_protocol.md (G4 — Live).
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root for run-as-script
from research.code.gates import pipeline
from research.code.infra.schema_ledger import SCHEMA_MT5

# Runnable as a SCRIPT, so the repo root is not on sys.path and the package
# import below would fail with ModuleNotFoundError (caught 2026-08-16 when
# handover_lint broke this way right after the task 357 repointing).
import sys as _sys, pathlib as _pl
_REPO = _pl.Path(__file__).resolve().parents[3]
if str(_REPO) not in _sys.path:
    _sys.path.insert(0, str(_REPO))
from research.code.infra.db_path import DB_PATH  # noqa: F401  (task 357: one canonical path)
MYT     = timezone(timedelta(hours=8))

# Provenance enums — where the ticks came from + how MT5 modelled them.
VALID_DATA_SOURCE    = ("dukascopy", "broker_history", "custom")
VALID_TESTER_MODEL   = ("real_ticks", "every_tick", "1min_ohlc", "open_only")
VALID_DIRECTION      = ("long", "short", "flat")
VALID_FIDELITY       = ("pass", "fail", "pending")


# Canonical DDL now lives in one place (task 287) — db_init.py used to keep a second,
# drifted copy of these tables. Do not re-inline it here.
_SCHEMA = SCHEMA_MT5


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> Path:
    """Create the Gate-7 + BRC tables in research.db. Idempotent (IF NOT EXISTS)."""
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    print(f"[tester] tester schema ready in {DB_PATH.name} (tester_runs/trades/zones)")
    return DB_PATH


def reset_fob_payload_tables(force: bool = False) -> dict:
    """Drop + recreate the 3 FOB payload tables (fob_cycles/fob_zones/fob_events) so a
    stale-schema husk is replaced by the CURRENT _SCHEMA (task 228 caught fob_zones still
    on the old single-retouch rt_count/rt_time shape vs the EA's 3-level rt1/2/3_time —
    ingest would column-mismatch on the task-220 re-emit).

    SAFETY: refuses unless every table is EMPTY (0 rows) — pass force=True to override.
    fob_run_stats is left alone (it is a rollup, keyed to run_id, and re-derived on ingest)."""
    tables = ["fob_events", "fob_zones", "fob_cycles"]  # child->parent order for the drop
    with _conn() as conn:
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        nonempty = {t: n for t, n in counts.items() if n}
        if nonempty and not force:
            raise RuntimeError(
                f"refusing to drop non-empty FOB payload tables: {nonempty} "
                f"(pass force=True only if you truly mean to discard rows)")
        conn.execute("PRAGMA foreign_keys = OFF")
        for t in tables:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.executescript(_SCHEMA)  # recreates from current schema (IF NOT EXISTS)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    print(f"[tester] FOB payload tables reset (dropped+recreated): {tables}  prior rows={counts}")
    return {"dropped": tables, "prior_counts": counts}


# ── Run header ────────────────────────────────────────────────────────────────
def ingest_tester_run(
    idea_id: str,
    symbol: str,
    data_source: str,
    ea_name: str = None,
    ea_version: str = None,
    model_quality: str = None,
    tester_model: str = None,
    timeframe: str = None,
    period_start: str = None,
    period_end: str = None,
    tz_offset_hours: int = None,
    magic_number: int = None,
    initial_deposit: float = None,
    leverage: int = None,
    spread_setting: str = None,
    params: dict = None,
    n_trades: int = None,
    net_profit_usd: float = None,
    profit_factor: float = None,
    max_dd_pct: float = None,
    win_rate: float = None,
    notes: str = None,
    run_role: str = None,
    git_sha: str = None,
    git_dirty: int = None,
) -> int:
    """Open a Strategy-Tester run with its data provenance + run-level summary.
    idea_id is soft-validated against research.db. Returns run_id. The FIDELITY diff
    columns are filled later via log_fidelity_diff()."""
    if not pipeline.get_idea(idea_id):
        raise ValueError(f"idea_id '{idea_id}' not found in research.db — register the idea first")
    if data_source not in VALID_DATA_SOURCE:
        raise ValueError(f"data_source must be one of {VALID_DATA_SOURCE}")
    if tester_model is not None and tester_model not in VALID_TESTER_MODEL:
        raise ValueError(f"tester_model must be one of {VALID_TESTER_MODEL} or None")
    if run_role is not None and run_role not in ("emitter", "trader"):
        raise ValueError("run_role must be 'emitter', 'trader', or None")
    params_json = json.dumps(params) if params is not None else None
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tester_runs
                (idea_id, ea_name, ea_version, symbol, data_source, model_quality,
                 tester_model, timeframe, period_start, period_end, tz_offset_hours,
                 magic_number, initial_deposit, leverage, spread_setting, params,
                 n_trades, net_profit_usd, profit_factor, max_dd_pct, win_rate,
                 notes, run_role, git_sha, git_dirty, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (idea_id, ea_name, ea_version, symbol, data_source, model_quality,
              tester_model, timeframe, period_start, period_end, tz_offset_hours,
              magic_number, initial_deposit, leverage, spread_setting, params_json,
              n_trades, net_profit_usd, profit_factor, max_dd_pct, win_rate,
              notes, run_role, git_sha, git_dirty, now, now))
        conn.commit()
        run_id = cur.lastrowid
    print(f"[tester] run #{run_id} {idea_id} {symbol} [{data_source}/{tester_model}] n={n_trades}")
    return run_id


def ingest_tester_trade(
    run_id: int,
    session_date: str = None,
    direction: str = None,
    entry_ts: str = None,
    entry_px: float = None,
    exit_ts: str = None,
    exit_px: float = None,
    exit_reason: str = None,
    lots: float = None,
    risk_unit: float = None,
    realized_R: float = None,
    realized_pnl_usd: float = None,
    ticket: int = None,
    meta: dict = None,
) -> int:
    """Record one closed tester round-trip. Cross-system join key = ticket + entry_ts
    (session_date is a nullable convenience for daily strategies). risk_unit is the
    generic 1R denominator (price units); strategy-specific context (ORB: or_high/
    or_low/range_w) goes in `meta` as JSON. Returns tt_id."""
    if direction is not None and direction not in VALID_DIRECTION:
        raise ValueError(f"direction must be one of {VALID_DIRECTION} or None")
    meta_json = json.dumps(meta) if meta is not None else None
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tester_trades
                (run_id, ticket, session_date, direction, entry_ts, entry_px,
                 exit_ts, exit_px, exit_reason, lots, risk_unit, realized_R,
                 realized_pnl_usd, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, ticket, session_date, direction, entry_ts, entry_px,
              exit_ts, exit_px, exit_reason, lots, risk_unit, realized_R,
              realized_pnl_usd, meta_json, now))
        conn.commit()
        tt_id = cur.lastrowid
    return tt_id


# ── BRC zone-lifecycle ingest (task 119) ───────────────────────────────────────
_ZONE_COLS = [
    "csv_zone_id", "tf", "direction",
    "p1_time", "p1_price", "p2_time", "p2_price", "p3_time", "p3_price",
    "p4_time", "p4_price", "p5_time", "p5_price",
    "l1", "l2", "mid", "break_kind",
    "t1_time", "t2_time", "t3_time", "confirm_time", "invalidation_time",
    "alive_at_end", "continued", "mfe_r", "mae_r", "realized_r", "bars_alive",
    "seq", "zone_key", "is_primary", "consolidated_into",
]
_ZONE_TIME_COLS  = {"p1_time", "p2_time", "p3_time", "p4_time", "p5_time",
                    "t1_time", "t2_time", "t3_time", "confirm_time", "invalidation_time"}
_ZONE_INT_COLS   = {"csv_zone_id", "alive_at_end", "continued", "bars_alive",
                    "seq", "is_primary"}
_ZONE_FLOAT_COLS = {"p1_price", "p2_price", "p3_price", "p4_price", "p5_price",
                    "l1", "l2", "mid", "mfe_r", "mae_r", "realized_r"}


def _norm_ts(s: str):
    """'YYYY.MM.DD HH:MM:SS' -> 'YYYY-MM-DD HH:MM:SS'; '' (0-sentinel) -> None.
    Only the date part carries dots (time uses ':'), so a blanket '.'→'-' is safe."""
    s = (s or "").strip()
    return s.replace(".", "-") if s else None


def ingest_brc_zones(run_id: int, csv_path) -> int:
    """Bulk-load a brc_csv.mqh lifecycle CSV (UTF-8, header, comma) into tester_zones
    under an existing tester_runs header. Returns the number of zone rows inserted.
    Re-ingesting the same run_id is blocked (delete the run's rows first to redo)."""
    import csv as _csv
    csv_path = Path(csv_path)
    if not get_tester_run(run_id):
        raise ValueError(f"tester run not found: {run_id} — create the run header first")
    with _conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM tester_zones WHERE run_id=?",
                                (run_id,)).fetchone()[0]
        if existing:
            raise ValueError(f"run #{run_id} already has {existing} zones — "
                             f"delete them before re-ingesting")

    now = _now()
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = _csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        # source header uses 'zone_id'; map it to csv_zone_id
        if "zone_id" not in header:
            raise ValueError(f"unexpected CSV header (no zone_id): {reader.fieldnames}")
        for r in reader:
            rec = {"csv_zone_id": r["zone_id"], "run_id": run_id, "created_at": now}
            for col in _ZONE_COLS:
                if col == "csv_zone_id":
                    continue
                v = r.get(col, "")
                if col in _ZONE_TIME_COLS:
                    rec[col] = _norm_ts(v)
                elif col in _ZONE_INT_COLS:
                    rec[col] = int(v) if str(v).strip() != "" else None
                elif col in _ZONE_FLOAT_COLS:
                    rec[col] = float(v) if str(v).strip() != "" else None
                else:
                    rec[col] = (v.strip() or None)
            rows.append(rec)

    cols = ["run_id"] + _ZONE_COLS + ["created_at"]
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO tester_zones ({', '.join(cols)}) VALUES ({placeholders})"
    with _conn() as conn:
        conn.executemany(sql, [tuple(rec[c] for c in cols) for rec in rows])
        conn.commit()
    print(f"[tester] run #{run_id} ingested {len(rows)} BRC zones from {csv_path.name}")
    return len(rows)


# ── FOB ingest: one wide capture CSV -> fob_cycles / fob_zones / fob_events ────
_RISK_MAP = {"LR": "LOW", "HR": "HIGH", "": None}

# Tier-C columns the EA emits as HEADER ONLY — every value is derived downstream. The
# emitter is a pristine causal oracle; the moment it starts writing an outcome column it
# has seen the future. `confirm_*` are the pre-task-261 names, still present in archived
# CSVs. (task 261)
_TIER_C_DERIVED = ("next_cf_time", "next_cf_price", "confirm_time", "confirm_price",
                   "continued", "mfe_r", "mae_r", "realized_r")


def _assert_tier_c_unpopulated(rows, csv_path):
    """Fail ingest if the emit CSV carries a value in any Tier-C outcome column.

    These are ingest-derived by definition. A populated one means the EA is emitting a
    forward-looking outcome, which would silently poison every screen built on the run."""
    if not rows:
        return
    present = [c for c in _TIER_C_DERIVED if c in rows[0]]
    dirty = {c: sum(1 for r in rows if str(r.get(c) or "").strip()) for c in present}
    bad = {c: n for c, n in dirty.items() if n}
    if bad:
        raise ValueError(
            f"emit CSV {Path(csv_path).name} populates Tier-C derived column(s) {bad} — "
            f"the EA must emit these header-only (task 261). A value here is look-ahead.")


def ingest_fob(run_id: int, csv_path) -> dict:
    """Derive fob_cycles / fob_zones / fob_events from a fob_capture_*.csv.

    Grain: ONE row per classified event (PBO/VR/CF); event<->zone is 1:1 at emit.
    Cycles are RECONSTRUCTED by grouping on (setup_tf, seq) — a NEW PBO = a NEW
    cycle (CLAUDE.md FOB rule). cycle_id / zone_id / event_id are surrogate keys
    assigned here (the EA never emits them). Returns a counts dict. Re-ingesting a
    run_id is blocked — delete_run(run_id, drop_run_row=False) first to redo.
    See docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md."""
    import csv as _csv
    from collections import OrderedDict
    csv_path = Path(csv_path)
    if not get_tester_run(run_id):
        raise ValueError(f"tester run not found: {run_id} — create the run header first")
    with _conn() as conn:
        for t in ("fob_events", "fob_zones", "fob_cycles"):
            n = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE run_id=?", (run_id,)).fetchone()[0]
            if n:
                raise ValueError(f"run #{run_id} already has {n} {t} rows — "
                                 f"delete them before re-ingesting")

    def _f(v):  # float or None
        v = str(v).strip(); return float(v) if v else None
    def _i(v):  # int or None
        v = str(v).strip(); return int(v) if v else None
    def _s(v):  # str or None
        v = str(v).strip(); return v or None

    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = _csv.DictReader(fh)
        need = {"setup_tf", "seq", "label", "event_tf", "htf_state", "level", "l2", "mid"}
        miss = need - set(reader.fieldnames or [])
        if miss:
            raise ValueError(f"CSV missing expected columns: {sorted(miss)}")
        rows = list(reader)

    _assert_tier_c_unpopulated(rows, csv_path)
    now = _now()

    # ── 1. reconstruct cycles by (setup_tf, seq), insertion order = chronological ─
    groups = OrderedDict()
    for r in rows:
        groups.setdefault((r["setup_tf"], int(r["seq"])), []).append(r)

    cycle_recs = []
    for (stf, seq), evs in groups.items():
        pbo = next((e for e in evs if e["label"] == "PBO"), evs[0])
        vr  = next((e for e in evs if e["label"] == "VR"), None)
        cfs = [e for e in evs if e["label"] in ("CF", "HRCF")]
        cf_times = sorted(t for t in (_norm_ts(e["bar_time"]) for e in cfs) if t)
        bar_times = sorted(t for t in (_norm_ts(e["bar_time"]) for e in evs) if t)
        inval = _norm_ts(pbo["invalidation_time"])
        status = "invalidated" if inval else ("alive" if str(pbo["alive_at_end"]).strip() == "1"
                                              else "complete")
        cycle_recs.append({
            "run_id": run_id, "setup_tf": stf, "seq": seq, "direction": _s(pbo["direction"]),
            "pbo_time": _norm_ts(pbo["bar_time"]), "pbo_level": _f(pbo["level"]),
            "pbo_swing_time": _norm_ts(pbo["swing_time"]), "pbo_bar_close": _f(pbo["bar_close"]),
            "vr_time": _norm_ts(vr["bar_time"]) if vr else None,
            "vr_level": _f(vr["level"]) if vr else None,
            "vr_made_first_tf": _s(vr["vr_made_first_tf"]) if vr else None,
            "n_cf": len(cfs),
            "first_cf_time": cf_times[0] if cf_times else None,
            "last_cf_time": cf_times[-1] if cf_times else None,
            "status": status, "invalidation_time": inval, "invalidated_by": None,
            "start_time": _norm_ts(pbo["bar_time"]),
            "end_time": bar_times[-1] if bar_times else None,
            "meta": json.dumps({"n_events": len(evs), "has_vr": vr is not None}),
            "created_at": now,
        })

    cyc_cols = ["run_id", "setup_tf", "seq", "direction", "pbo_time", "pbo_level",
                "pbo_swing_time", "pbo_bar_close", "vr_time", "vr_level", "vr_made_first_tf",
                "n_cf", "first_cf_time", "last_cf_time", "status", "invalidation_time",
                "invalidated_by", "start_time", "end_time", "meta", "created_at"]
    zone_cols = ["run_id", "cycle_id", "source_label", "event_tf", "direction", "l1", "l2",
                 "mid", "p1_time", "p1_price", "p3_time", "p3_price", "t1_time", "t2_time",
                 "t3_time", "n_l1_touches", "n_mid_touches", "n_l2_touches", "rt1_time",
                 "rt2_time", "rt3_time", "vr_fresh", "next_cf_time", "next_cf_price", "invalidation_time",
                 "continued", "alive_at_end", "bars_alive", "mfe_r", "mae_r", "realized_r",
                 "zone_key", "is_primary", "superseded_by", "zone_valid", "meta", "created_at"]
    evt_cols = ["run_id", "cycle_id", "zone_id", "event_tf", "label", "cf_idx", "risk_class",
                "direction", "swing_time", "bar_time", "level", "bar_close", "body_clears",
                "vr_zone_broken", "htf_state", "meta", "created_at"]

    def _ins(cur, table, cols, rec):
        ph = ", ".join("?" for _ in cols)
        cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({ph})",
                    tuple(rec[c] for c in cols))
        return cur.lastrowid

    with _conn() as conn:
        cur = conn.cursor()
        # cycles first -> (setup_tf, seq) -> cycle_id
        key2cid = {}
        for cr in cycle_recs:
            key2cid[(cr["setup_tf"], cr["seq"])] = _ins(cur, "fob_cycles", cyc_cols, cr)
        # then zone + event per CSV row (original chronological order)
        n_z = n_e = 0
        for r in rows:
            cid = key2cid[(r["setup_tf"], int(r["seq"]))]
            src = "CF" if r["label"] == "HRCF" else r["label"]
            zrec = {
                "run_id": run_id, "cycle_id": cid, "source_label": src,
                "event_tf": r["event_tf"], "direction": _s(r["direction"]),
                "l1": _f(r["level"]), "l2": _f(r["l2"]), "mid": _f(r["mid"]),
                "p1_time": _norm_ts(r["p1_time"]), "p1_price": _f(r["p1_price"]),
                "p3_time": _norm_ts(r["p3_time"]), "p3_price": _f(r["p3_price"]),
                "t1_time": _norm_ts(r["t1_time"]), "t2_time": _norm_ts(r["t2_time"]),
                "t3_time": _norm_ts(r["t3_time"]), "n_l1_touches": _i(r["n_l1_touches"]),
                "n_mid_touches": _i(r["n_mid_touches"]), "n_l2_touches": _i(r["n_l2_touches"]),
                "rt1_time": _norm_ts(r["rt1_time"]), "rt2_time": _norm_ts(r["rt2_time"]),
                "rt3_time": _norm_ts(r["rt3_time"]),
                "vr_fresh": _i(r["vr_fresh"]),
                # Tier-C: header-only in the CSV (asserted empty above), derived downstream.
                "next_cf_time": None, "next_cf_price": None,
                "invalidation_time": _norm_ts(r["invalidation_time"]),
                "continued": None, "alive_at_end": _i(r["alive_at_end"]),
                "bars_alive": _i(r["bars_alive"]),
                "mfe_r": None, "mae_r": None, "realized_r": None,
                "zone_key": _s(r["zone_key"]), "is_primary": _i(r["is_primary"]),
                "superseded_by": _s(r["superseded_by"]), "zone_valid": _i(r["zone_valid"]),
                "meta": None, "created_at": now,
            }
            zid = _ins(cur, "fob_zones", zone_cols, zrec); n_z += 1
            erec = {
                "run_id": run_id, "cycle_id": cid, "zone_id": zid, "event_tf": r["event_tf"],
                "label": r["label"], "cf_idx": _i(r["cf_idx"]),
                "risk_class": _RISK_MAP.get(str(r["risk_class"]).strip(), None),
                "direction": _s(r["direction"]), "swing_time": _norm_ts(r["swing_time"]),
                "bar_time": _norm_ts(r["bar_time"]), "level": _f(r["level"]),
                "bar_close": _f(r["bar_close"]), "body_clears": _i(r["body_clears"]),
                "vr_zone_broken": _i(r["vr_zone_broken"]), "htf_state": _s(r["htf_state"]),
                "meta": None, "created_at": now,
            }
            _ins(cur, "fob_events", evt_cols, erec); n_e += 1
        conn.commit()

    counts = {"cycles": len(cycle_recs), "zones": n_z, "events": n_e}
    print(f"[tester] run #{run_id} ingested FOB: {counts['cycles']} cycles, "
          f"{counts['zones']} zones, {counts['events']} events from {csv_path.name}")
    return counts


def derive_fob_confirm_linkage(run_id: int) -> dict:
    """Phase-2 Part A (task 200) — set zone.next_cf_time / next_cf_price for CF zones from
    NEXT-CF LINKAGE within each cycle (the next same-cycle CF that the storyline printed).
    Deterministic, no external data. NOTE: this is ONLY the linkage pointer — it does NOT
    decide win/loss. The outcome (continued / realized_r) is a forward PRICE result owned by
    derive_fob_tier_c_outcome() (next-CF linkage alone is degenerate ~99% 'continued').
    Idempotent.

    LOOK-AHEAD WARNING (task 261) — these fields are non-null iff a later CF exists in the
    cycle, i.e. exactly `cf_idx < max_cf`. Selecting or filtering on them conditions on the
    future and manufactures survivorship. Renamed from confirm_time/confirm_price, whose name
    invited exactly that: a screen anchored entries on `confirm_time` and produced a fake
    t+7.72. Any entry anchor MUST be the CF event's own bar_time."""
    if not get_tester_run(run_id):
        raise ValueError(f"tester run not found: {run_id}")
    with _conn() as conn:
        rows = conn.execute("""
            SELECT z.zone_id, z.cycle_id, e.cf_idx, e.bar_time, e.level
            FROM fob_zones z
            JOIN fob_events e ON e.zone_id = z.zone_id
            WHERE z.run_id = ? AND z.source_label = 'CF'
            ORDER BY z.cycle_id, e.cf_idx, e.bar_time
        """, (run_id,)).fetchall()
        from collections import OrderedDict
        cyc = OrderedDict()
        for zid, cid, cf_idx, bar_time, level in rows:
            cyc.setdefault(cid, []).append((zid, bar_time, level))
        updates = []
        for cid, cfs in cyc.items():
            for i, (zid, bt, lv) in enumerate(cfs):
                nxt = cfs[i + 1] if i + 1 < len(cfs) else None
                updates.append((nxt[1] if nxt else None, nxt[2] if nxt else None, zid))
        conn.executemany(
            "UPDATE fob_zones SET next_cf_time=?, next_cf_price=? WHERE zone_id=?", updates)
        conn.commit()
    print(f"[tester] run #{run_id} Tier-C(next-CF linkage): {len(updates)} CF zones linked")
    return {"cf_zones": len(updates)}


def derive_fob_tier_c_outcome(run_id: int, target_r: float = 2.0,
                              symbol_loader=None) -> dict:
    """Phase-2 Part B (task 200) — derive zone.continued + realized_r for CF zones via a
    forward FIXED-2R-vs-1R BARRIER sweep on M1 mid bars (entry=l1, stop=l2, R=|l1-l2|,
    target=entry +/- target_r*R by direction). EXPLORATORY mid-price (M1 high/low first-
    touch) — NOT a money result; the MT5 tester is the arbiter (CLAUDE.md trust rule).

    win  (continued=1, realized_r=+target_r): target touched before stop.
    loss (continued=0, realized_r=-1.0)     : stop touched first (incl. same-bar tie -> stop,
                                              conservative — high & low both cross in one M1).
    censored (continued/realized_r NULL)    : neither touched by the end of available M1 bars.

    Numba kernel; idempotent (overwrites). symbol_loader override = test seam (default M1)."""
    import numpy as np
    import pandas as pd
    from numba import njit

    if not get_tester_run(run_id):
        raise ValueError(f"tester run not found: {run_id}")
    with _conn() as conn:
        rows = conn.execute("""
            SELECT z.zone_id, z.direction, z.l1, z.l2, e.bar_time
            FROM fob_zones z JOIN fob_events e ON e.zone_id = z.zone_id
            WHERE z.run_id = ? AND z.source_label = 'CF'
              AND z.l1 IS NOT NULL AND z.l2 IS NOT NULL AND z.l1 != z.l2
              AND z.direction IN ('BUY','SELL')
            ORDER BY e.bar_time
        """, (run_id,)).fetchall()
    if not rows:
        print(f"[tester] run #{run_id} Tier-C(outcome): no eligible CF zones")
        return {"cf_zones": 0}

    zids = np.array([r[0] for r in rows], dtype=np.int64)
    is_buy = np.array([1 if r[1] == "BUY" else 0 for r in rows], dtype=np.int8)
    l1 = np.array([float(r[2]) for r in rows])
    l2 = np.array([float(r[3]) for r in rows])
    R = np.abs(l1 - l2)
    target = np.where(is_buy == 1, l1 + target_r * R, l1 - target_r * R)
    entry_ts = pd.to_datetime([r[4] for r in rows], utc=True)

    # M1 mid bars covering [first entry, end]; high/low drive first-touch.
    loader = symbol_loader or (lambda s, e: _m1_for_outcome(s, e))
    bars = loader(entry_ts.min(), None)
    bt = bars.index.values.astype("datetime64[ns]")
    highs = bars["high"].to_numpy(); lows = bars["low"].to_numpy()
    start_idx = np.searchsorted(bt, entry_ts.values.astype("datetime64[ns]"), side="left")

    @njit(cache=True)
    def _sweep(start_idx, is_buy, stop, target, highs, lows):
        n = start_idx.shape[0]; nb = highs.shape[0]
        out = np.empty(n, dtype=np.int8)  # 1 win, 0 loss, -1 censored
        for k in range(n):
            i0 = start_idx[k]
            res = -1
            for i in range(i0, nb):
                hi = highs[i]; lo = lows[i]
                if is_buy[k] == 1:
                    hit_stop = lo <= stop[k]; hit_tgt = hi >= target[k]
                else:
                    hit_stop = hi >= stop[k]; hit_tgt = lo <= target[k]
                if hit_stop:           # tie -> stop first (conservative)
                    res = 0; break
                if hit_tgt:
                    res = 1; break
            out[k] = res
        return out

    codes = _sweep(start_idx, is_buy, l2, target, highs, lows)

    updates = []
    n_win = n_loss = n_cens = 0
    for zid, c in zip(zids, codes):
        if c == 1:   updates.append((1, float(target_r), int(zid)));  n_win += 1
        elif c == 0: updates.append((0, -1.0, int(zid)));             n_loss += 1
        else:        updates.append((None, None, int(zid)));          n_cens += 1
    with _conn() as conn:
        conn.executemany(
            "UPDATE fob_zones SET continued=?, realized_r=? WHERE zone_id=?", updates)
        conn.commit()

    resolved = n_win + n_loss
    hit = (n_win / resolved) if resolved else float("nan")
    print(f"[tester] run #{run_id} Tier-C(outcome @ {target_r}R): {len(updates)} CF zones -> "
          f"win={n_win} loss={n_loss} censored={n_cens}  hit-rate={hit:.4f}")
    return {"cf_zones": len(updates), "win": n_win, "loss": n_loss,
            "censored": n_cens, "hit_rate": hit, "target_r": target_r}


def derive_fob_run_stats(run_id: int) -> dict:
    """Task 228 — roll the raw fob_* payload up into ONE row per (run_id, setup_tf) in
    fob_run_stats: a small permanent CONCLUSION so downstream screens (task 182 RT-edge
    by setup-TF, conditioner sweeps) read ~7-60 rows instead of scanning ~768k raw rows.
    Round-1 columns per docs/specs/2026-07-03_fob_payload_dataplane_split.md.

    setup_tf lives on the CYCLE, so zone stats join through cycle_id. Aggregates use AVG
    (SQLite skips NULLs); rt_count = # of non-null rt{1,2,3}_time per zone (0-3);
    vr_fresh_pct / win_pct average only over zones where the flag is populated.
    Idempotent (DELETE + re-insert for this run_id)."""
    if not get_tester_run(run_id):
        raise ValueError(f"tester run not found: {run_id}")
    now = _now()
    with _conn() as conn:
        # cycle-level (setup_tf is a cycle column): n_cycles, n_cf
        cyc = conn.execute("""
            SELECT setup_tf,
                   COUNT(*)               AS n_cycles,
                   COALESCE(SUM(n_cf), 0) AS n_cf
            FROM fob_cycles WHERE run_id = ?
            GROUP BY setup_tf
        """, (run_id,)).fetchall()
        # zone-level (join to cycle for setup_tf)
        zon = conn.execute("""
            SELECT c.setup_tf,
                   COUNT(*) AS n_zones,
                   AVG( (CASE WHEN z.rt1_time IS NOT NULL THEN 1 ELSE 0 END)
                      + (CASE WHEN z.rt2_time IS NOT NULL THEN 1 ELSE 0 END)
                      + (CASE WHEN z.rt3_time IS NOT NULL THEN 1 ELSE 0 END) ) AS mean_rt_count,
                   AVG(z.n_l2_touches) AS mean_n_l2_touches,
                   100.0 * AVG(CASE WHEN z.vr_fresh  IS NOT NULL THEN z.vr_fresh  END) AS vr_fresh_pct,
                   AVG(z.realized_r) AS mean_realized_r,
                   AVG(z.mfe_r)      AS mean_mfe_r,
                   AVG(z.mae_r)      AS mean_mae_r,
                   100.0 * AVG(CASE WHEN z.continued IS NOT NULL THEN z.continued END) AS win_pct,
                   AVG(z.bars_alive) AS mean_bars_alive
            FROM fob_zones z JOIN fob_cycles c ON c.cycle_id = z.cycle_id
            WHERE z.run_id = ?
            GROUP BY c.setup_tf
        """, (run_id,)).fetchall()
        zmap = {r["setup_tf"]: r for r in zon}

        recs = []
        for cr in cyc:
            stf = cr["setup_tf"]
            z = zmap.get(stf)
            recs.append((
                run_id, stf, cr["n_cycles"], (z["n_zones"] if z else 0), cr["n_cf"],
                (z["mean_rt_count"]     if z else None),
                (z["mean_n_l2_touches"] if z else None),
                (z["vr_fresh_pct"]      if z else None),
                (z["mean_realized_r"]   if z else None),
                (z["mean_mfe_r"]        if z else None),
                (z["mean_mae_r"]        if z else None),
                (z["win_pct"]           if z else None),
                (z["mean_bars_alive"]   if z else None),
                now,
            ))
        conn.execute("DELETE FROM fob_run_stats WHERE run_id = ?", (run_id,))
        conn.executemany("""
            INSERT INTO fob_run_stats
              (run_id, setup_tf, n_cycles, n_zones, n_cf, mean_rt_count, mean_n_l2_touches,
               vr_fresh_pct, mean_realized_r, mean_mfe_r, mean_mae_r, win_pct, mean_bars_alive,
               created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, recs)
        conn.commit()
    print(f"[tester] run #{run_id} fob_run_stats: {len(recs)} setup_tf rollup row(s)")
    return {"setup_tf_rows": len(recs)}


def _m1_for_outcome(start, end):
    """M1 mid bars for the barrier sweep, reading across the seal (research-internal,
    not a forward-leak: outcomes are labels on past zones). Local import keeps arctic
    optional for non-FOB callers."""
    from research.code.io import arctic_io
    return arctic_io.m1_bars(start=start, end=end, columns=["high", "low"])


def log_fidelity_diff(
    run_id: int,
    research_result_id: int,
    trade_overlap_pct: float,
    ER_delta_vs_research: float,
    R_corr: float,
    verdict: str,
    gate_answer: str = None,
    answered_by: str = "human",
    allow_incomplete: bool = False,
) -> None:
    """Write the FIDELITY diff against the Python research result and set the verdict.

    On verdict='pass' this calls pipeline.pass_gate(idea_id, 4, ...) — the precondition
    execution.register_deployment() / open_deploy_gate('FORWARD') read. On 'fail' it
    blocks G4 (the port is not the validated strategy). Pre-commit the equivalence
    thresholds before computing the diff (gate_answer should record them + the numbers)."""
    if verdict not in VALID_FIDELITY:
        raise ValueError(f"verdict must be one of {VALID_FIDELITY}")
    run = get_tester_run(run_id)
    if not run:
        raise ValueError(f"tester run not found: {run_id}")
    idea_id = run["idea_id"]
    now = _now()
    with _conn() as conn:
        conn.execute("""
            UPDATE tester_runs
            SET research_result_id=?, trade_overlap_pct=?, ER_delta_vs_research=?,
                R_corr=?, fidelity_verdict=?, updated_at=?
            WHERE run_id=?
        """, (research_result_id, trade_overlap_pct, ER_delta_vs_research, R_corr,
              verdict, now, run_id))
        conn.commit()
    answer = gate_answer or (
        f"FIDELITY {verdict}: overlap={trade_overlap_pct}%, "
        f"ER_delta={ER_delta_vs_research}, R_corr={R_corr} (run #{run_id})"
    )
    print(f"[tester] run #{run_id} FIDELITY diff: {verdict} "
          f"(overlap={trade_overlap_pct}%, ER_delta={ER_delta_vs_research}, R_corr={R_corr})")
    # Drive the research gate from the verdict.
    if verdict == "pass":
        if not _g4_open(idea_id):
            pipeline.open_gate(idea_id, 4,
                               pass_criteria="overlap>=95%, E[R]/win/$per-t in research 95% CI, high R_corr")
        pipeline.pass_gate(idea_id, 4, answer, answered_by=answered_by,
                           allow_incomplete=allow_incomplete)
    elif verdict == "fail":
        if not _g4_open(idea_id):
            pipeline.open_gate(idea_id, 4,
                               pass_criteria="overlap>=95%, E[R]/win/$per-t in research 95% CI, high R_corr")
        pipeline.block_gate(idea_id, 4, answer, answered_by=answered_by)


def _g4_open(idea_id: str) -> bool:
    """True if a G4 gate row already exists for this idea (any status)."""
    return any(g["gate_number"] == 4 for g in pipeline.get_gates(idea_id))


def get_tester_run(run_id: int) -> dict:
    """Return the tester_runs row as a dict (empty if not found)."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tester_runs WHERE run_id=?", (run_id,)).fetchone()
    return dict(row) if row else {}


def gate4_passed(idea_id: str) -> bool:
    """True iff G4 (Live/FIDELITY) is 'passed' for this idea — the live-side gate that
    execution.py checks before a deployment may exist."""
    gates = pipeline.get_gates(idea_id)
    return any(g["gate_number"] == 4 and g["status"] == "passed" for g in gates)


def delete_run(run_id: int, drop_run_row: bool = True) -> dict:
    """Hard-delete one emitter/trader run's data from research.db: its payload
    (tester_zones [BRC] + fob_cycles/fob_events/fob_zones [FOB]), tester_trades,
    tester_run_summary, and (optionally) the tester_runs row itself. Returns the
    deleted-row counts. Destructive + irreversible — caller must have explicit human
    authorization (CLAUDE.md rule 2). Re-emit + re-ingest to restore."""
    with _conn() as conn:
        meta = conn.execute(
            "SELECT idea_id, ea_name FROM tester_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        # FOB payload: events/zones reference cycles -> delete children first
        fe = conn.execute("DELETE FROM fob_events WHERE run_id=?", (run_id,)).rowcount
        fz = conn.execute("DELETE FROM fob_zones  WHERE run_id=?", (run_id,)).rowcount
        fc = conn.execute("DELETE FROM fob_cycles WHERE run_id=?", (run_id,)).rowcount
        z = conn.execute("DELETE FROM tester_zones WHERE run_id=?", (run_id,)).rowcount
        t = conn.execute("DELETE FROM tester_trades WHERE run_id=?", (run_id,)).rowcount
        conn.execute("DELETE FROM tester_run_summary WHERE run_id=?", (run_id,))
        r = 0
        if drop_run_row:
            r = conn.execute("DELETE FROM tester_runs WHERE run_id=?", (run_id,)).rowcount
        conn.commit()
    out = {"run_id": run_id, "idea_id": meta["idea_id"] if meta else None,
           "ea_name": meta["ea_name"] if meta else None,
           "zones_deleted": z, "fob_zones_deleted": fz, "fob_events_deleted": fe,
           "fob_cycles_deleted": fc, "trades_deleted": t, "run_rows_deleted": r}
    print(f"[tester] delete_run {run_id} ({out['idea_id']}/{out['ea_name']}): "
          f"brc_zones={z} fob(c/z/e)={fc}/{fz}/{fe} trades={t} run_row={r}")
    return out


def clear_fob_payload_run(run_id: int) -> dict:
    """Task 229 (Lever 2) — clear ONE run's raw FOB payload rows (fob_cycles/
    fob_zones/fob_events) from research.db after they have been exported to Parquet
    (research.code.io.fob_payload.export_run). Keeps the run header (tester_runs) and
    the rollup (fob_run_stats) — those are the CONCLUSIONS research.db retains.
    Reversible: re-export from the Parquet, or re-ingest the emit CSV. Children
    (events/zones reference cycles) are deleted first."""
    with _conn() as conn:
        fe = conn.execute("DELETE FROM fob_events WHERE run_id=?", (run_id,)).rowcount
        fz = conn.execute("DELETE FROM fob_zones  WHERE run_id=?", (run_id,)).rowcount
        fc = conn.execute("DELETE FROM fob_cycles WHERE run_id=?", (run_id,)).rowcount
        conn.commit()
    print(f"[tester] clear_fob_payload_run {run_id}: cleared fob(c/z/e)={fc}/{fz}/{fe} "
          f"(header + fob_run_stats kept)")
    return {"run_id": run_id, "fob_cycles_cleared": fc,
            "fob_zones_cleared": fz, "fob_events_cleared": fe}


def vacuum() -> Path:
    """VACUUM research.db — rebuilds the file so freed pages (e.g. after
    clear_fob_payload_run) are reclaimed to the OS. Must run outside a transaction."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("VACUUM")
    finally:
        conn.close()
    print(f"[tester] VACUUM {DB_PATH.name} done")
    return DB_PATH


if __name__ == "__main__":
    init_db()


# ─────────────────────────────────────────────────────────────────────────────
# DISABLED by migration 038 (2026-08-16). fob_cycles / fob_zones / fob_events /
# fob_run_stats were dropped: the ledger no longer carries strategy-shaped tables.
# These six functions staged raw FOB payload INTO those tables, so they cannot run.
#
# To restore FOB ingest, rewrite it to write Parquet directly into
# research/data/fob_payload/run_<id>/ — no DB staging step at all. That is the agreed
# direction (finished output -> files, live mutable state -> DB) and it removes the
# export-then-clear dance these functions existed to perform.
#
# Already-ingested runs are UNAFFECTED: their Parquet is on disk and
# fob_payload.read_fob_payload() still reads it.
# ─────────────────────────────────────────────────────────────────────────────
_FOB_INGEST_DISABLED = (
    "FOB DB-staging ingest is disabled: migration 038 dropped fob_cycles/fob_zones/"
    "fob_events/fob_run_stats. Rewrite this path to write Parquet directly "
    "(research/data/fob_payload/run_<id>/) before calling it. Reading existing runs "
    "still works via fob_payload.read_fob_payload()."
)


def _fob_disabled(*_a, **_k):
    raise NotImplementedError(_FOB_INGEST_DISABLED)

reset_fob_payload_tables = _fob_disabled
ingest_fob = _fob_disabled
derive_fob_confirm_linkage = _fob_disabled
derive_fob_tier_c_outcome = _fob_disabled
derive_fob_run_stats = _fob_disabled
clear_fob_payload_run = _fob_disabled

# DISABLED by migration 039 (2026-08-16): tester_trades / tester_zones /
# tester_run_summary were dropped — bulk per-run payload lives in files keyed by the
# run_id in the path, not in the ledger. tester_runs (the registry) is unaffected, so
# ingest_tester_run / get_tester_run / log_fidelity_diff still work.
_TESTER_PAYLOAD_DISABLED = (
    "tester payload ingest is disabled: migration 039 dropped tester_trades/tester_zones/"
    "tester_run_summary. Write per-trade output to Parquet under a run_<id>/ path and "
    "register the run in tester_runs instead."
)


def _tester_payload_disabled(*_a, **_k):
    raise NotImplementedError(_TESTER_PAYLOAD_DISABLED)


ingest_tester_trade = _tester_payload_disabled
ingest_brc_zones = _tester_payload_disabled

# Migration 040 dropped tester_runs, the last table this module wrote to. Every remaining
# entry point below depended on it, so the whole ingest/fidelity surface is now inert.
# It is kept (not deleted) because the SHAPE is worth reusing: a generic `runs` registry
# with a `platform` column is the agreed design for baysix.db. Port these then, against
# that table, with per-trade output going to Parquet instead of the ledger.
_TESTER_RUNS_GONE = (
    "tester_runs was dropped by migration 040 — research.db is a pure spine now. "
    "Rebuild against the generic `runs` registry when it lands in baysix.db."
)


def _tester_runs_gone(*_a, **_k):
    raise NotImplementedError(_TESTER_RUNS_GONE)


init_db = _tester_runs_gone
ingest_tester_run = _tester_runs_gone
get_tester_run = _tester_runs_gone
delete_run = _tester_runs_gone
log_fidelity_diff = _tester_runs_gone
gate4_passed = _tester_runs_gone
