"""
Task 292 — read one grw_meta.mq5 pass off disk and put it where it belongs.

The EA writes three artifacts into the MT5 COMMON files folder per pass:

    grw_run_<tag>.csv       one row  — the pass summary (fitness, growth, telemetry)
    grw_params_<tag>.json   the exact GrwCfg that ran
    grw_trades_<tag>.csv    one row per closed round-trip

This script is the ONLY sanctioned path from those files into research.db. It opens a
`tester_runs` header, fills `tester_trades`, and — only when a registered batch is named
— records the pass via grw.log_pass(). Every write goes through research/code/ (CLAUDE.md
rule 10); the protocol_guard hook blocks raw sqlite3 anyway.

WHAT THIS SCRIPT REFUSES TO DO
  * write a grw_passes row without a REGISTERED batch. A pass with no pre-registration
    behind it has no promote_if to be judged against later, and a row that can never be
    adjudicated silently inflates the trial denominator (spec §2.2/§2.3).
  * write anything to step4_results. A pass is RAW MATERIAL. Only grw.adjudicate() at S3
    and grw.promote() at S4 may create a result — the agent gets no vote.

Usage:
    # plumbing only — tester_runs + tester_trades, no grw_passes row
    python research/code/io/ingest_grw.py --tag XAUUSD_dukas_v0.1.0_20160613_smoke

    # a real pre-registered pass
    python research/code/io/ingest_grw.py --tag <tag> --batch-id grw-2026-08-04-001
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.code.io import tester
from research.code.gates import grw

_REPO = Path(__file__).resolve().parents[3]

#--- MT5 COMMON files folder. Overridable for a non-default MetaQuotes install.
_COMMON = Path(os.environ.get(
    "MT5_COMMON_FILES",
    Path.home() / "AppData/Roaming/MetaQuotes/Terminal/Common/Files"))


def _git_provenance():
    """(short_sha, dirty_flag) for HEAD, or (None, None) if git is unavailable."""
    try:
        sha = subprocess.check_output(["git", "-C", str(_REPO), "rev-parse", "--short", "HEAD"],
                                      text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(_REPO), "status", "--porcelain"],
                                        text=True).strip()
        return sha, (1 if dirty else 0)
    except Exception:
        return None, None


#--- Task 309. The tick source is a PROPERTY OF THE SYMBOL, not a constant. XAUUSD_dukas is a
#--- custom symbol built from dukascopy history; XAUUSD.s is JustMarkets' own live feed, and the
#--- two disagree on spread, session boundaries and the min-lot arithmetic the $20 mandate lives
#--- on. Stamping every pass "dukascopy" made a JM-fed run cite a source it never touched.
#--- Unknown symbols RAISE rather than defaulting — a wrong provenance string is worse than a
#--- refused ingest, because it survives into every downstream citation silently.
_DATA_SOURCE_BY_SUFFIX = (
    (".s",      "justmarkets"),   # JM live/demo server symbols carry the .s suffix
    ("_dukas",  "dukascopy"),     # custom symbol imported from dukascopy ticks
    ("_pq",     "arctic"),        # custom symbol imported from our own parquet/Arctic store
)


def _data_source_for(symbol: str) -> str:
    """Derive the tick provenance from the tester symbol. Raises on an unmapped symbol."""
    sym = (symbol or "").strip()
    for suffix, source in _DATA_SOURCE_BY_SUFFIX:
        if sym.endswith(suffix):
            return source
    raise SystemExit(
        f"unmapped symbol {sym!r} — add its suffix to _DATA_SOURCE_BY_SUFFIX in ingest_grw.py. "
        "Refusing to guess the tick source; a wrong data_source is unrecoverable downstream.")


def _f(row: dict, key: str, cast=float, default=None):
    """Read a CSV cell, tolerating a blank. A missing KEY is a contract break and raises —
    the EA and this reader must agree on the schema or the pass is not ingestible."""
    if key not in row:
        raise KeyError(f"column {key!r} missing from the run summary — EA/reader schema drift")
    v = (row[key] or "").strip()
    if v == "":
        return default
    return cast(v)


def read_pass(tag: str, common: Path = _COMMON) -> dict:
    """Load the three artifacts for `tag` into one dict. Raises if any is missing."""
    run_csv = common / f"grw_run_{tag}.csv"
    par_json = common / f"grw_params_{tag}.json"
    trd_csv = common / f"grw_trades_{tag}.csv"
    for p in (run_csv, par_json, trd_csv):
        if not p.exists():
            raise SystemExit(f"missing artifact: {p}")

    rows = list(csv.DictReader(open(run_csv, newline="", encoding="utf-8", errors="replace")))
    if len(rows) != 1:
        raise SystemExit(f"{run_csv.name} must hold exactly one data row, found {len(rows)}")
    summary = rows[0]

    params = json.loads(par_json.read_text(encoding="utf-8", errors="replace"))
    trades = list(csv.DictReader(open(trd_csv, newline="", encoding="utf-8", errors="replace")))
    return {"summary": summary, "params": params, "trades": trades}


def ingest(tag: str, batch_id: str = None, idea_id: str = "GRW-001",
           leg: str = "is", notes: str = None, common: Path = _COMMON) -> dict:
    """tester_runs + tester_trades (+ optional grw_passes). Returns ids and counts."""
    if leg not in ("is", "oos"):
        raise ValueError("leg must be 'is' or 'oos'")

    art = read_pass(tag, common)
    s, params, trades = art["summary"], art["params"], art["trades"]
    sha, dirty = _git_provenance()
    tester.init_db()

    #--- provenance the EA stamped at ITS compile time beats whatever HEAD is now.
    ea_sha = (s.get("git_sha") or "").strip() or sha
    ea_dirty = _f(s, "git_dirty", int, dirty)

    run_id = tester.ingest_tester_run(
        idea_id=idea_id,
        symbol=s.get("symbol"),
        data_source="dukascopy",
        ea_name=s.get("ea_name") or "grw_meta",
        ea_version=s.get("ea_version"),
        tester_model="real_ticks",
        timeframe=(s.get("tf") or "").replace("PERIOD_", ""),
        period_start=(s.get("period_start") or "").replace(".", "-") or None,
        period_end=(s.get("period_end") or "").replace(".", "-") or None,
        initial_deposit=_f(s, "initial_deposit"),
        params=params,
        n_trades=_f(s, "n_trades", int),
        net_profit_usd=_f(s, "net_usd"),
        profit_factor=_f(s, "profit_factor"),
        max_dd_pct=_f(s, "max_dd_pct"),
        win_rate=_f(s, "win_rate"),
        magic_number=params.get("magic"),
        run_role="trader",
        git_sha=ea_sha,
        git_dirty=ea_dirty,
        notes=notes or f"GRW {leg.upper()} pass from {tag}"
             + (f" (batch {batch_id})" if batch_id else " (no batch — plumbing only)"),
    )

    for t in trades:
        tester.ingest_tester_trade(
            run_id=run_id,
            direction=(t.get("direction") or "").upper() or None,
            entry_ts=(t.get("entry_ts") or "").replace(".", "-") or None,
            entry_px=_f(t, "entry_px"),
            exit_ts=(t.get("exit_ts") or "").replace(".", "-") or None,
            exit_px=_f(t, "exit_px"),
            lots=_f(t, "lots"),
            risk_unit=_f(t, "risk_unit"),
            realized_R=_f(t, "realized_R"),
            realized_pnl_usd=_f(t, "realized_pnl_usd"),
            ticket=_f(t, "position_id", int),
            meta={"tag": t.get("tag"),
                  "commission": _f(t, "commission"),
                  "swap": _f(t, "swap")},
        )

    out = {"run_id": run_id, "n_trades_csv": len(trades), "pass_id": None}

    #--- SIZING VALIDITY: say it loudly at ingest, because by the time this number is
    #--- read off a scoreboard nobody remembers whether the risk fraction was honoured.
    if s.get("sizing_valid") == "0":
        print(f"[grw-ingest] WARNING run #{run_id}: clamp_up_frac="
              f"{_f(s, 'clamp_up_frac', float, 0.0):.1%} — the equity fraction was NOT "
              f"honoured. This pass measured a FIXED-LOT strategy; its growth is not a "
              f"compounding claim.")
    if s.get("unrankable") == "1":
        print(f"[grw-ingest] WARNING run #{run_id}: UNRANKABLE "
              f"(n_trades={_f(s, 'n_trades', int)}) — fitness is a sentinel, not a score.")

    #--- SCALP VIABILITY: a stop too tight for the venue is a DIFFERENT failure from a stop
    #--- that was allowed and lost. Tolerate the column being absent so v0.1.0 summaries
    #--- still ingest, but shout when a material share of signals never reached the broker.
    _tight = _f(s, "n_sl_too_tight", int, 0) if "n_sl_too_tight" in s else 0
    _sig = _f(s, "n_signals", int, 0)
    if _tight > 0 and _sig > 0:
        print(f"[grw-ingest] NOTE run #{run_id}: {_tight}/{_sig} signals "
              f"({_tight / _sig:.1%}) were dropped for a stop inside the broker min-distance "
              f"or the live spread — the config's stop is too tight for this venue at those "
              f"moments, which is a VENUE result, not a strategy result.")

    if not batch_id:
        print(f"[grw-ingest] run #{run_id} ingested WITHOUT a grw_passes row "
              f"(no --batch-id). Nothing here can be adjudicated or promoted.")
        return out

    #--- a pass row requires a registered batch: the prereg is what gives it a verdict.
    if leg == "is":
        out["pass_id"] = grw.log_pass(
            batch_id=batch_id,
            params=params,
            is_run_id=run_id,
            is_fitness=_f(s, "fitness"),
            is_growth=_f(s, "growth"),
            is_n_trades=_f(s, "n_trades", int),
            is_net_usd=_f(s, "net_usd"),
            is_max_dd_pct=_f(s, "max_dd_pct"),
        )
        print(f"[grw-ingest] S0 pass #{out['pass_id']} logged for batch {batch_id}")
    else:
        raise SystemExit(
            "OOS legs attach to an EXISTING pass, not a new one. Run grw.record_oos("
            "pass_id=..., oos_run_id=%d, ...) with the pass_id from the in-sample leg."
            % run_id)

    return out


def main():
    ap = argparse.ArgumentParser(description="Ingest one grw_meta pass into research.db")
    ap.add_argument("--tag", required=True,
                    help="run tag, e.g. XAUUSD_dukas_v0.1.0_20160613_smoke")
    ap.add_argument("--batch-id", default=None,
                    help="registered batch; omit for a plumbing-only ingest (no grw_passes row)")
    ap.add_argument("--idea-id", default="GRW-001")
    ap.add_argument("--leg", default="is", choices=("is", "oos"))
    ap.add_argument("--notes", default=None)
    ap.add_argument("--common", default=None, help="override the MT5 COMMON files folder")
    args = ap.parse_args()

    common = Path(args.common) if args.common else _COMMON
    res = ingest(args.tag, batch_id=args.batch_id, idea_id=args.idea_id,
                 leg=args.leg, notes=args.notes, common=common)
    print(f"[grw-ingest] done: run_id={res['run_id']} trades={res['n_trades_csv']} "
          f"pass_id={res['pass_id']}")


if __name__ == "__main__":
    main()
