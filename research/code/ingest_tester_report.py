"""
Ingest an MT5 Strategy-Tester report (.xlsx) into research.db Gate-7 evidence and
rename the file by its run_id — so the file on disk maps 1:1 to its tester_runs row.

MT5 always exports the report as 'ReportTester-<login>.xlsx' (same name every run, so
each export overwrites the last). This tool:
  1. parses the report header (Expert, Symbol, Period, Inputs, Deposit, History Quality)
     + the run-level Results summary (net profit, PF, max DD%, win-rate, n_trades),
  2. writes a tester_runs row via research.code.tester.ingest_tester_run() -> run_id,
  3. renames/moves the file to  run{run_id:03d}_{idea}_{source}_dep{dep}_{start}_{end}.xlsx
     under mt5/strategy_tester_xlsx/  (preserving it before the next run overwrites it).

Per-trade ingest (tester_trades) for the FIDELITY diff is task 43 — the .xlsx Deals
section has price/time/PnL but NOT range_w (the 1R unit), so realized_R needs the EA
to export a per-trade CSV (or_high/or_low/range_w). That hook is left as ingest_trades().

Usage:
    python research/code/ingest_tester_report.py --dry-run         # parse + show, no write
    python research/code/ingest_tester_report.py                   # ingest newest + rename
    python research/code/ingest_tester_report.py --src <file.xlsx> # explicit file
"""
import re
import sys
import json
import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # openpyxl default-style noise
import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.code import tester

REPORT_DIR = Path(__file__).resolve().parents[1].parent / "mt5" / "strategy_tester_xlsx"
RAW_GLOB = "ReportTester-*.xlsx"


# ── parsing ─────────────────────────────────────────────────────────────────────
def _rows(path: Path) -> list[tuple]:
    wb = openpyxl.load_workbook(path, read_only=True)
    return list(wb.active.iter_rows(values_only=True))


def _val_right(row: tuple, label: str):
    """In a row, find the cell == label (or startswith) and return the next non-empty
    cell to its right as a string."""
    cells = list(row)
    for i, c in enumerate(cells):
        if c is not None and str(c).strip().rstrip(":").lower() == label.lower():
            for nxt in cells[i + 1:]:
                if nxt is not None and str(nxt).strip() != "":
                    return str(nxt).strip()
    return None


def _find(rows, label: str):
    """Scan all rows for a label, return the value to its right (first hit)."""
    for row in rows:
        v = _val_right(row, label)
        if v is not None:
            return v
    return None


def _find_contains(rows, needle: str):
    """Return (cell_text, value_to_right) for the first cell containing `needle`."""
    for row in rows:
        cells = list(row)
        for i, c in enumerate(cells):
            if c is not None and needle.lower() in str(c).lower():
                for nxt in cells[i + 1:]:
                    if nxt is not None and str(nxt).strip() != "":
                        return str(c).strip(), str(nxt).strip()
    return None, None


def _num(s):
    if s is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    return float(m.group()) if m else None


def _pct(s):
    """Pull a percentage out of e.g. '34 (30.63%)' or '36.65 (62.53%)'."""
    if s is None:
        return None
    m = re.search(r"\(([\d.]+)%\)", s)
    return float(m.group(1)) if m else None


def parse_report(path: Path) -> dict:
    rows = _rows(path)
    ea_name = _find(rows, "Expert")
    symbol  = _find(rows, "Symbol")
    period  = _find(rows, "Period") or ""
    deposit = _num(_find(rows, "Initial Deposit"))
    lev_raw = _find(rows, "Leverage")                      # '1:3000' -> 3000
    lev     = _num(lev_raw.split(":")[-1]) if lev_raw else None
    quality = _find(rows, "History Quality")

    # period: 'M1 (2024.05.01 - 2026.05.30)'
    tf_m = re.match(r"\s*(\w+)", period)
    dates = re.findall(r"(\d{4})\.(\d{2})\.(\d{2})", period)
    timeframe = tf_m.group(1) if tf_m else None
    p_start = f"{dates[0][0]}-{dates[0][1]}-{dates[0][2]}" if dates else None
    p_end   = f"{dates[1][0]}-{dates[1][1]}-{dates[1][2]}" if len(dates) > 1 else None

    # inputs: every 'Key=Value' cell anywhere in the sheet
    inputs = {}
    for row in rows:
        for c in row:
            if c is not None and re.fullmatch(r"Inp\w+=.*", str(c).strip()):
                k, _, v = str(c).strip().partition("=")
                inputs[k] = v
    magic = int(inputs["InpMagic"]) if "InpMagic" in inputs else None

    # provenance
    data_source = "dukascopy" if "dukas" in (symbol or "").lower() else "broker_history"
    tester_model = "real_ticks" if quality and "real tick" in quality.lower() else None

    # idea_id from EA name: baysix_orb_001 -> ORB-001
    idea_id = None
    em = re.search(r"orb[_-]?(\d+)", ea_name or "", re.I)
    if em:
        idea_id = f"ORB-{int(em.group(1)):03d}"

    # run-level summary (label-scan; positions vary)
    net   = _num(_find(rows, "Total Net Profit"))
    pf    = _num(_find(rows, "Profit Factor"))
    n_tr  = _num(_find(rows, "Total Trades"))
    win_c, win_v = _find_contains(rows, "Profit Trades")   # '34 (30.63%)'
    win_rate = _pct(win_v)
    dd_c, dd_v = _find_contains(rows, "Equity Drawdown Maximal")
    max_dd_pct = _pct(dd_v)

    return {
        "idea_id": idea_id, "ea_name": ea_name, "symbol": symbol,
        "data_source": data_source, "model_quality": quality, "tester_model": tester_model,
        "timeframe": timeframe, "period_start": p_start, "period_end": p_end,
        "magic_number": magic, "initial_deposit": deposit,
        "leverage": int(lev) if lev else None, "params": inputs,
        "n_trades": int(n_tr) if n_tr else None, "net_profit_usd": net,
        "profit_factor": pf, "max_dd_pct": max_dd_pct, "win_rate": win_rate,
    }


# ── filename ────────────────────────────────────────────────────────────────────
def _dep_tag(dep) -> str:
    if not dep:
        return "depNA"
    d = int(dep)
    return f"dep{d // 1000}k" if d >= 1000 and d % 1000 == 0 else f"dep{d}"


def canonical_name(run_id: int, p: dict) -> str:
    return (f"run{run_id:03d}_{p['idea_id']}_{p['data_source']}_"
            f"{_dep_tag(p['initial_deposit'])}_{p['period_start']}_{p['period_end']}.xlsx")


def newest_raw(src_dir: Path) -> Path | None:
    raws = sorted(src_dir.glob(RAW_GLOB), key=lambda f: f.stat().st_mtime, reverse=True)
    return raws[0] if raws else None


# ── main ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="explicit .xlsx (default: newest ReportTester-*.xlsx in mt5/strategy_tester_xlsx)")
    ap.add_argument("--dry-run", action="store_true", help="parse + show, no DB write / rename")
    args = ap.parse_args()

    src = Path(args.src) if args.src else newest_raw(REPORT_DIR)
    if not src or not src.exists():
        print(f"no report found (looked for {RAW_GLOB} in {REPORT_DIR})")
        sys.exit(1)

    p = parse_report(src)
    print(f"=== parsed {src.name} ===")
    for k in ("idea_id", "ea_name", "symbol", "data_source", "tester_model", "timeframe",
              "period_start", "period_end", "magic_number", "initial_deposit", "leverage",
              "n_trades", "net_profit_usd", "profit_factor", "max_dd_pct", "win_rate"):
        print(f"  {k:16} = {p[k]}")

    if not p["idea_id"]:
        print("ERROR: could not derive idea_id from EA name — aborting"); sys.exit(1)

    if args.dry_run:
        print(f"\n[dry-run] would ingest tester_runs row + rename to:")
        print(f"  run???_{p['idea_id']}_{p['data_source']}_{_dep_tag(p['initial_deposit'])}_"
              f"{p['period_start']}_{p['period_end']}.xlsx  (run_id filled on real run)")
        print("[dry-run] no DB write, no file moved")
        return

    run_id = tester.ingest_tester_run(
        idea_id=p["idea_id"], symbol=p["symbol"], data_source=p["data_source"],
        ea_name=p["ea_name"], model_quality=p["model_quality"], tester_model=p["tester_model"],
        timeframe=p["timeframe"], period_start=p["period_start"], period_end=p["period_end"],
        magic_number=p["magic_number"], initial_deposit=p["initial_deposit"],
        leverage=p["leverage"], params=p["params"], n_trades=p["n_trades"],
        net_profit_usd=p["net_profit_usd"], profit_factor=p["profit_factor"],
        max_dd_pct=p["max_dd_pct"], win_rate=p["win_rate"],
        notes=f"ingested from {src.name}",
    )
    new_path = REPORT_DIR / canonical_name(run_id, p)
    src.rename(new_path)
    print(f"\n[ok] tester_runs run_id={run_id}")
    print(f"[ok] renamed -> {new_path.name}")
    print(f"     per-trade ingest (tester_trades) + FIDELITY diff = task 43 (needs EA range_w CSV)")


if __name__ == "__main__":
    main()
