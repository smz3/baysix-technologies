"""
ORB-001 D0 — feed/logic PARITY gate (pre-deployment, NO live EA required).

WHY (task 4, deployment_dgate_sequence): before porting ORB-001 into the Sigma
MQL5 EA, prove the LIVE feed (JustMarkets) produces the SAME opening-range SIGNAL
as the research feed (Dukascopy). If the feeds disagree on the 09:00 UTC range,
the whole port is built on sand. D0 certifies the SIGNAL layer only:
    direction (long/short) + OR-high/OR-low + entry price.
Trail-exit fill realism is a D1 concern (live fills vs model), not D0.

FROZEN LIVE CONFIG (strategy_log.get_live_config('ORB-001')):
    anchor 09:00 UTC / N=5 min / trail_1R exit / Mode-A min-lot 5% cap.
Only the anchor (09:00) + window (N=5) drive the SIGNAL; that is what D0 replays.

GRANULARITY DECISION: research = Dukascopy TICKS, live = JM BARS. Comparing
tick-ORs vs bar-ORs would conflate granularity noise with true feed divergence.
So D0 runs on M1 BARS for BOTH feeds — resample Dukascopy ticks -> M1, pull JM as
M1 — and runs the SAME bar-based OR logic on each. This also matches what the live
EA actually sees (bars).

TWO MODES:
    --source dukas  (default) : DRY self-parity. Live feed = Dukascopy (same window).
                                Must yield 0 direction mismatches + 0 pip divergence
                                -> validates the harness plumbing end-to-end.
    --source jm               : LIVE. Live feed = JustMarkets via mt5.copy_rates_range
                                (requires the MT5 terminal open + logged into JM demo).

DB: dry mode writes to a THROWAWAY temp execution.db (real DB stays clean) unless
--commit is passed. --source jm always commits to the real execution.db.

    python -X utf8 research/models/orb/orb001/d0_parity.py --source dukas
    python -X utf8 research/models/orb/orb001/d0_parity.py --source jm --commit

PASS CRITERIA (pre-committed): direction_mismatch == 0
    AND boundary divergence median <= 2 pip AND max <= 5 pip.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from research.models.orb.orb001 import orb_core

# ── Frozen-config constants ──────────────────────────────────────────────────
IDEA_ID         = "ORB-001"
INSTRUMENT      = "XAUUSD.s"
ANCHOR_HOUR     = 9          # 09:00 UTC (frozen live config, task 22)
N_MINUTES       = 5
SEARCH_END_HOUR = 21         # EOD-flat boundary (matches anchor_oos EOD_HOUR)

# XAUUSD pip = 0.10 price ($/oz): a "2-pip" spread = 0.20 (equity_sim / justmarkets.yaml).
PIP_PRICE = 0.10
MED_TOL_PIP = 2.0            # pre-committed pass tolerance (median daily OR-boundary div)
MAX_TOL_PIP = 5.0            # pre-committed pass tolerance (worst single session)

# JustMarkets bars are server time GMT+3, naive -> shift -3h to UTC.
SYMBOL = "XAUUSD.s"
JM_SERVER_UTC_OFFSET_H = 3

# Deployment identity for D0 (JM demo account).
ACCOUNT_ID = "JM-DEMO-ORB"
DEPLOY_ID  = f"{IDEA_ID}@{ACCOUNT_ID}"

PASS_CRITERIA = ("direction_mismatch==0 AND boundary_div_median_pip<=2 "
                 "AND boundary_div_max_pip<=5")


# ── Frozen-config SIGNAL recompute (bar-based, anchor-parametrized) ──────────
def orb_signal_bars(bars_1m: pd.DataFrame,
                    anchor_hour: int = ANCHOR_HOUR,
                    n_minutes: int = N_MINUTES,
                    search_end_hour: int = SEARCH_END_HOUR) -> pd.DataFrame:
    """Per day: opening range over [anchor, anchor+N) UTC, then the FIRST breakout
    of range high/low after the window closes (no look-ahead). Bar high/low based,
    so it runs identically on Dukascopy-M1 and JM-M1.

    Mirrors orb_core.opening_range_breakouts but with a settable anchor_hour (the
    core module hardcodes 08:00; the frozen live config is 09:00). Returns one row
    per day: or_high, or_low, range_w, direction (long/short/none), break_ts, entry_px.
    """
    rows = []
    days = list(bars_1m.groupby(bars_1m.index.normalize()))
    for day, g in tqdm(days, desc=f"ORB {anchor_hour:02d}:00/N={n_minutes}", leave=False):
        anchor = day + pd.Timedelta(hours=anchor_hour)
        or_win = g[(g.index >= anchor) & (g.index < anchor + pd.Timedelta(minutes=n_minutes))]
        if or_win.empty:
            continue  # holiday / no session this day at this anchor

        or_hi = float(or_win["high"].max())
        or_lo = float(or_win["low"].min())

        post = g[(g.index >= anchor + pd.Timedelta(minutes=n_minutes)) &
                 (g.index < day + pd.Timedelta(hours=search_end_hour))]

        long_hit = post.index[post["high"] > or_hi]
        short_hit = post.index[post["low"] < or_lo]
        t_long = long_hit[0] if len(long_hit) else None
        t_short = short_hit[0] if len(short_hit) else None

        if t_long is None and t_short is None:
            direction, btime, entry = "none", None, np.nan
        elif t_short is None or (t_long is not None and t_long <= t_short):
            direction, btime, entry = "long", t_long, or_hi
        else:
            direction, btime, entry = "short", t_short, or_lo

        rows.append({
            "date": day.date(), "or_high": or_hi, "or_low": or_lo,
            "range_w": or_hi - or_lo, "direction": direction,
            "break_ts": btime, "entry_px": entry,
        })

    return pd.DataFrame(rows).set_index("date")


# ── Feed loaders (both return UTC-indexed [open, high, low, close] M1) ────────
def _available_months() -> list[tuple[int, int]]:
    """Sorted (year, month) Dukascopy tick partitions present on disk."""
    out = []
    for p in orb_core._TICK_DIR.glob("year=*/month=*"):
        try:
            yr = int(p.parents[0].name.split("=")[1])
            mo = int(p.name.split("=")[1])
            out.append((yr, mo))
        except (IndexError, ValueError):
            continue
    return sorted(set(out))


def load_dukas_m1(window_days: int) -> pd.DataFrame:
    """Dukascopy ticks -> M1 mid OHLC, last `window_days` of available history."""
    months = _available_months()
    if not months:
        raise FileNotFoundError(f"no Dukascopy partitions under {orb_core._TICK_DIR}")
    n_months = max(2, window_days // 28 + 1)
    bars = orb_core.load_minute_bars(months[-n_months:], is_only=False)
    end = bars.index.max().normalize()
    start = end - pd.Timedelta(days=window_days)
    return bars[bars.index >= start]


def load_jm_m1(window_days: int) -> pd.DataFrame:
    """JustMarkets M1 OHLC via the running MT5 terminal, last `window_days`, in UTC."""
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise SystemExit(f"mt5.initialize failed: {mt5.last_error()} "
                         f"(is the JM terminal open + Algo Trading enabled?)")
    ti, ai = mt5.terminal_info(), mt5.account_info()
    print(f"[bridge] terminal={ti.company} connected={ti.connected} "
          f"server={ai.server if ai else '?'} login={ai.login if ai else '?'}")
    if not mt5.symbol_select(SYMBOL, True):
        mt5.shutdown()
        raise SystemExit(f"symbol_select {SYMBOL} failed: {mt5.last_error()}")

    # copy_rates_range takes server-time (GMT+3) datetimes; ask for a generous span.
    end_srv = pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(hours=JM_SERVER_UTC_OFFSET_H)
    start_srv = end_srv - pd.Timedelta(days=window_days + 3)
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1,
                                 start_srv.to_pydatetime(), end_srv.to_pydatetime())
    err = mt5.last_error()
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise SystemExit(f"JM copy_rates_range returned no data ({err})")

    df = pd.DataFrame(rates)
    # server time (GMT+3, naive) -> UTC
    t = pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=JM_SERVER_UTC_OFFSET_H)
    df = df.set_index(t)[["open", "high", "low", "close"]]
    df.index.name = None
    end = df.index.max().normalize()
    start = end - pd.Timedelta(days=window_days)
    return df[df.index >= start]


# ── Diff: logic parity + feed divergence ─────────────────────────────────────
def compare(sig_ref: pd.DataFrame, sig_live: pd.DataFrame) -> dict:
    """Align signals on session date; return parity + divergence metrics."""
    common = sig_ref.index.intersection(sig_live.index)
    ref = sig_ref.loc[common]
    live = sig_live.loc[common]

    dir_mismatch = int((ref["direction"].values != live["direction"].values).sum())

    # boundary divergence (pips) over days where BOTH feeds saw a session (always,
    # since a row exists per session day for both).
    hi_div = np.abs(ref["or_high"].values - live["or_high"].values) / PIP_PRICE
    lo_div = np.abs(ref["or_low"].values - live["or_low"].values) / PIP_PRICE
    bnd_div = np.concatenate([hi_div, lo_div])

    return {
        "n_common": int(len(common)),
        "n_ref_only": int(len(sig_ref.index.difference(sig_live.index))),
        "n_live_only": int(len(sig_live.index.difference(sig_ref.index))),
        "direction_mismatch": dir_mismatch,
        "or_high_div_median_pip": float(np.median(hi_div)) if len(hi_div) else 0.0,
        "or_low_div_median_pip": float(np.median(lo_div)) if len(lo_div) else 0.0,
        "boundary_div_median_pip": float(np.median(bnd_div)) if len(bnd_div) else 0.0,
        "boundary_div_max_pip": float(np.max(bnd_div)) if len(bnd_div) else 0.0,
        "boundary_div_p95_pip": float(np.percentile(bnd_div, 95)) if len(bnd_div) else 0.0,
    }


def verdict(m: dict) -> bool:
    return (m["direction_mismatch"] == 0
            and m["boundary_div_median_pip"] <= MED_TOL_PIP
            and m["boundary_div_max_pip"] <= MAX_TOL_PIP)


# ── execution.db writes ──────────────────────────────────────────────────────
def _ensure_registered(execution) -> None:
    """Idempotently register the JM demo account + the ORB-001 deployment."""
    if not execution.get_account_rules(ACCOUNT_ID):
        execution.register_account(
            ACCOUNT_ID, venue="justmarkets", account_type="retail_highlev",
            mode="demo", base_currency="USD", leverage=3000, initial_balance=50.0,
            max_total_dd_pct=None, dd_basis="static",
        )
    if not execution.get_deploy_config(DEPLOY_ID):
        execution.register_deployment(IDEA_ID, ACCOUNT_ID, instrument=INSTRUMENT)


def _persist(execution, sig_live: pd.DataFrame, metrics: dict, passed: bool) -> None:
    """Log live recompute signals, recon metrics, and resolve the D0 gate."""
    _ensure_registered(execution)

    # 1) live recompute signals (actionable trades only: long/short)
    anchor_label = f"{ANCHOR_HOUR:02d}:00 UTC"
    for day, r in sig_live.iterrows():
        if r["direction"] not in ("long", "short"):
            continue
        stop_px = r["or_low"] if r["direction"] == "long" else r["or_high"]
        sig_ts = (r["break_ts"].strftime("%Y-%m-%d %H:%M:%S")
                  if pd.notna(r["break_ts"]) else f"{day} {ANCHOR_HOUR:02d}:{N_MINUTES:02d}:00")
        execution.log_signal(
            DEPLOY_ID, direction=r["direction"], signal_ts=sig_ts,
            session_date=str(day), intended_entry_px=float(r["entry_px"]),
            intended_stop_px=float(stop_px), intended_size=0.01,
            meta={"or_high": float(r["or_high"]), "or_low": float(r["or_low"]),
                  "range_w": float(r["range_w"]), "anchor": anchor_label},
        )

    # 2) recon metrics (the lie-detector record)
    n = metrics["n_common"]
    for k in ("direction_mismatch", "boundary_div_median_pip",
              "boundary_div_max_pip", "boundary_div_p95_pip",
              "or_high_div_median_pip", "or_low_div_median_pip"):
        execution.log_recon_result(DEPLOY_ID, metric_key=k,
                                   metric_value=float(metrics[k]),
                                   n_obs=n, gate_number=0)

    # 3) gate (guardrail requires recon rows first — satisfied above)
    gate_id = execution.open_deploy_gate(DEPLOY_ID, 0, PASS_CRITERIA)
    answer = (f"dir_mismatch={metrics['direction_mismatch']} "
              f"bnd_div median={metrics['boundary_div_median_pip']:.2f}pip "
              f"max={metrics['boundary_div_max_pip']:.2f}pip (n={n})")
    if passed:
        execution.pass_deploy_gate(DEPLOY_ID, 0, answer)
        execution.log_deploy_change(DEPLOY_ID, verdict="PROMOTED", from_stage="D0",
                                    to_stage="D0", rationale="D0 feed/logic parity passed: " + answer)
    else:
        execution.block_deploy_gate(DEPLOY_ID, 0, answer)
    print(f"[d0] gate_id={gate_id} {'PASSED' if passed else 'BLOCKED'}")


# ── Orchestration ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="ORB-001 D0 feed/logic parity gate")
    ap.add_argument("--source", choices=["dukas", "jm"], default="dukas",
                    help="live feed: dukas = dry self-parity, jm = JustMarkets live")
    ap.add_argument("--window-days", type=int, default=45)
    ap.add_argument("--commit", action="store_true",
                    help="write to the REAL execution.db (jm always commits)")
    args = ap.parse_args()

    commit = args.commit or args.source == "jm"

    # Dry mode writes to a throwaway temp execution.db unless --commit.
    if not commit:
        tmp = REPO / "research" / "outputs" / "orb" / "d0" / "execution_d0_dry.db"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        if tmp.exists():
            tmp.unlink()
        os.environ["EXECUTION_DB_PATH"] = str(tmp)

    from research.code import execution
    execution.init_db()

    print("=" * 88)
    print(f"ORB-001 D0 — FEED/LOGIC PARITY  (source={args.source}, window={args.window_days}d)")
    print(f"  frozen config: anchor {ANCHOR_HOUR:02d}:00 UTC / N={N_MINUTES} / trail_1R / ModeA-5%")
    print(f"  pass: dir_mismatch==0 AND bnd_div median<={MED_TOL_PIP}pip AND max<={MAX_TOL_PIP}pip")
    print(f"  exec.db: {'REAL' if commit else 'TEMP (dry)'}")
    print("=" * 88)

    # 1) load both feeds (M1, UTC)
    print("[1] loading research feed (Dukascopy ticks -> M1) ...")
    ref_bars = load_dukas_m1(args.window_days)
    if args.source == "jm":
        print("[2] loading live feed (JustMarkets M1 via MT5) ...")
        live_bars = load_jm_m1(args.window_days)
    else:
        print("[2] live feed = Dukascopy (DRY self-parity) ...")
        live_bars = ref_bars.copy()

    # sanity block (protocol rule 5)
    print("\n[sanity]")
    print(f"  ref  bars: {len(ref_bars):>7,}  {ref_bars.index.min()} -> {ref_bars.index.max()}")
    print(f"  live bars: {len(live_bars):>7,}  {live_bars.index.min()} -> {live_bars.index.max()}")
    if len(ref_bars) == 0 or len(live_bars) == 0:
        sys.exit("*** empty feed — aborting before compute.")

    # 2) recompute frozen-config signals on each feed
    print("\n[3] recompute ORB signals (09:00/N5) on both feeds ...")
    sig_ref = orb_signal_bars(ref_bars)
    sig_live = orb_signal_bars(live_bars)
    print(f"  ref  sessions: {len(sig_ref)}  (long={int((sig_ref.direction=='long').sum())} "
          f"short={int((sig_ref.direction=='short').sum())} none={int((sig_ref.direction=='none').sum())})")
    print(f"  live sessions: {len(sig_live)}  (long={int((sig_live.direction=='long').sum())} "
          f"short={int((sig_live.direction=='short').sum())} none={int((sig_live.direction=='none').sum())})")

    # 3) diff
    print("\n[4] diff (logic parity + feed divergence) ...")
    m = compare(sig_ref, sig_live)
    passed = verdict(m)
    print("-" * 88)
    for k, v in m.items():
        print(f"  {k:>28}: {v}")
    print("-" * 88)
    print(f"  VERDICT: {'PASS' if passed else 'BLOCK'} "
          f"(dir_mismatch={m['direction_mismatch']}, "
          f"bnd median={m['boundary_div_median_pip']:.2f}pip, max={m['boundary_div_max_pip']:.2f}pip)")
    print("=" * 88)

    # 4) persist to execution.db
    print("\n[5] writing to execution.db ...")
    _persist(execution, sig_live, m, passed)
    print("\n[d0] done.")


if __name__ == "__main__":
    main()
