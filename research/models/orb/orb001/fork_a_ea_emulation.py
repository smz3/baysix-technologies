"""
ORB-001 Gate-7 Fork A — EA-faithful bid/ask fill emulation (backlog task 47).

WHY THIS EXISTS
---------------
Gate-7 surfaced a contradiction on the SAME month/config/spread (May-2024,
09:00/N=5/trail_1R, synthetic 2-pip):
    Python idealized (anchor_oos._simulate_day):  23 trades, 56.5% win, +67.4R
    MT5 Strategy Tester (baysix_orb_001.ex5):     22 trades, 13.6% win, -$11
Diagnosis: a FILL-MODEL convention gap. Python validates on mid + 1/2-spread
TOLERANCE; the EA trades raw bid/ask with NO tolerance. For ORB-001's tiny
range (~$0.4-1.0) the ~$0.10 gap flips trade DIRECTION on the big-trend days.

Fork A re-implements the EA's EXACT conventions in Python, on the IDENTICAL
synthetic ticks the tester traded (bid/ask = parquet_mid +/- 0.10, see
export_ticks_mt5.HALF_SPREAD), and runs them side-by-side with the Python
idealized model.

DECISIVE TEST
-------------
  * If the EA-faithful column reproduces ~13% win / negative  -> root cause is
    100% confirmed AND the +67.4R is proven to be an idealized-fill artifact.
  * Whatever the EA-faithful column shows IS the honest, realistic-fill edge
    (it is a real bid/ask path sim) -> it is the number that should gate a port.

EA CONVENTIONS REPLICATED (from baysix_orb_001.mq5)
---------------------------------------------------
  OR      : built from M1 bar hi/lo => max/min BID over [anchor, or_close)   (L193-217)
  entry   : first tick with bid>=or_high (long) or bid<=or_low (short), NO tol (L272-276)
  fill    : long fills at ASK, short fills at BID (market order)             (L292-304)
  seed    : g_peak = entry fill price                                        (L305)
  stop0   : opposite OR boundary (or_low for long / or_high for short)       (L290)
  trail   : long peak=max bid, sl=peak-range_w (raise only); fires bid<=sl   (L333-338)
            short peak=min ask, sl=peak+range_w (lower only); fires ask>=sl  (L339-344)
  exit    : stop fills at the stop level (sl); EOD market-closes at bid/ask  (L146-151)

    python -X utf8 research/models/orb/orb001/fork_a_ea_emulation.py
    python -X utf8 research/models/orb/orb001/fork_a_ea_emulation.py 2024-05

Outputs -> research/outputs/orb/fork_a/
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files, IS_END
from research.models.orb.orb001.anchor_oos import _simulate_day  # Python idealized (mid+tol)

IS_CUT = np.datetime64(IS_END)  # 2024-05-02 sealed IS/OOS boundary

# --- frozen live config (strategy_log.get_live_config('ORB-001')) ---
ANCHOR_HOUR = 9.0
N_MINUTES   = 5
EOD_HOUR    = 21
HALF_SPREAD = 0.10          # MUST equal export_ticks_mt5.HALF_SPREAD (tester ticks)
LOT         = 0.01
CONTRACT    = 100.0         # XAUUSD oz/lot
EQUITY      = 10_000.0      # tester deposit (risk-cap context; cap rarely binds at 10k)
RISK_CAP_PCT = 5.0

NS_H = 3_600_000_000_000
NS_M =    60_000_000_000
NS_D = 86_400_000_000_000
_OUT = REPO / "research" / "outputs" / "orb" / "fork_a"


# ---------------------------------------------------------------------------
# EA-faithful per-day sim — raw bid/ask, no tolerance, exactly as the .mq5 EA.
# Returns dollar PnL + R (= PnL / risk_usd) so it ties to the tester report.
# ---------------------------------------------------------------------------
def _simulate_day_ea(ts, bid, ask, day0):
    anchor   = day0 + int(ANCHOR_HOUR * NS_H)
    or_close = anchor + N_MINUTES * NS_M
    eod      = day0 + EOD_HOUR * NS_H

    in_or = (ts >= anchor) & (ts < or_close)
    if not in_or.any():
        return None
    or_high = float(bid[in_or].max())       # MT5 bars are BID-based -> OR from bid
    or_low  = float(bid[in_or].min())
    range_w = or_high - or_low
    if range_w <= 0:
        return None

    post = np.where((ts >= or_close) & (ts < eod))[0]
    if len(post) == 0:
        return None

    # --- entry: first tick breaching either boundary on BID, no tolerance ---
    dir_ = 0; ei = None
    for k in post:
        b = bid[k]
        if b >= or_high:
            dir_ = 1; ei = k; break
        if b <= or_low:
            dir_ = -1; ei = k; break
    if dir_ == 0:
        return {"range_w": range_w, "traded": False, "R": 0.0, "pnl": 0.0}

    risk_usd = range_w * CONTRACT * LOT
    if RISK_CAP_PCT > 0 and EQUITY > 0 and (risk_usd / EQUITY) * 100.0 > RISK_CAP_PCT:
        return {"range_w": range_w, "traded": False, "skipped": True, "R": 0.0, "pnl": 0.0}

    # ticks from entry to EOD (entry tick inclusive for peak seed)
    seg = np.arange(ei, post[-1] + 1)
    B = bid[seg]; A = ask[seg]

    if dir_ == 1:                                  # LONG: fill at ask, trail on bid
        entry = float(A[0])
        peak  = entry                              # g_peak = fill price (L305)
        sl    = or_low                             # stop0 = opposite boundary (L290)
        exit_px = float(B[-1])                     # default EOD close at bid
        why = "EOD"
        for j in range(1, len(seg)):
            if B[j] > peak:
                peak = B[j]
            want = peak - range_w
            if want > sl:                          # raise only
                sl = want
            if B[j] <= sl:                         # stop fires on bid -> fill at sl
                exit_px = sl; why = "TRAIL"; break
        pnl = (exit_px - entry) * CONTRACT * LOT
    else:                                          # SHORT: fill at bid, trail on ask
        entry = float(B[0])
        peak  = entry
        sl    = or_high
        exit_px = float(A[-1])
        why = "EOD"
        for j in range(1, len(seg)):
            if A[j] < peak:
                peak = A[j]
            want = peak + range_w
            if want < sl:                          # lower only
                sl = want
            if A[j] >= sl:
                exit_px = sl; why = "TRAIL"; break
        pnl = (entry - exit_px) * CONTRACT * LOT

    return {"range_w": range_w, "traded": True, "dir": dir_, "R": pnl / risk_usd,
            "pnl": pnl, "exit": why}


def _scan_month(files, model, oos_only=False):
    """model in {'ea','ideal'} -> list of per-trade dicts with R (and pnl for ea)."""
    rows = []
    for f in tqdm(files, desc=f"{model} scan", leave=False):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]).sort_values("ts_utc")
        tsv = df["ts_utc"].values
        if oos_only:
            df = df[tsv >= IS_CUT]
            if df.empty:
                continue
        ts  = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid = (df["bid"].values + df["ask"].values) * 0.5          # native mid
        bid = mid - HALF_SPREAD                                    # synthetic 2-pip = tester ticks
        ask = mid + HALF_SPREAD
        day_key = ts // NS_D
        for d in np.unique(day_key):
            mk = day_key == d
            day0 = int(d) * NS_D
            if model == "ea":
                r = _simulate_day_ea(ts[mk], bid[mk], ask[mk], day0)
                if r is not None and r.get("traded"):
                    rows.append(r)
            else:
                # Python idealized: mid + 1/2-spread tolerance (verbatim _simulate_day)
                r = _simulate_day(ts[mk], mid[mk], day0, ANCHOR_HOUR, N_MINUTES)
                if r is not None:
                    rows.append({"range_w": r["range_w"], "R": r["R"], "pnl": None})
    return rows


def _stats(rows, with_dollars=False):
    if not rows:
        return {"n": 0}
    R  = np.array([r["R"] for r in rows], float)
    rw = np.array([r["range_w"] for r in rows], float)
    n = len(R); mu = float(R.mean()); sd = float(R.std(ddof=1))
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    out = {"n": n, "win_pct": round(float((R > 0).mean()) * 100, 1),
           "sum_R": round(float(R.sum()), 2), "E_R": round(mu, 4),
           "t_stat": round(mu / se, 2) if sd > 0 and n > 1 else None,
           "dollar_per_trade_R": round(float((R * rw).mean()), 4)}
    if with_dollars:
        pnl = np.array([r["pnl"] for r in rows], float)
        out["net_usd"] = round(float(pnl.sum()), 2)
        out["mean_usd"] = round(float(pnl.mean()), 4)
    return out


def _month_range(a: str, b: str | None):
    y0, m0 = int(a[:4]), int(a[5:7])
    y1, m1 = (int(b[:4]), int(b[5:7])) if b else (y0, m0)
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append((y, m)); m += 1
        if m > 12:
            m = 1; y += 1
    return out


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    start = sys.argv[1] if len(sys.argv) > 1 else "2024-05"
    end   = sys.argv[2] if len(sys.argv) > 2 else None
    months = _month_range(start, end)
    files = _tick_files(months)
    if not files:
        sys.exit(f"no parquet tick files for {start}..{end}")
    span = f"{start}" if end is None else f"{start}..{end}"
    is_full_oos = len(months) > 1
    tag_out = "fork_a_oos" if is_full_oos else "fork_a"

    print("=" * 92)
    print(f"ORB-001 FORK A — EA-faithful bid/ask emulation vs Python idealized   span={span}")
    print(f"  config: anchor {ANCHOR_HOUR:g}:00 / N={N_MINUTES} / trail_1R / "
          f"spread={2*HALF_SPREAD:.2f} (mid+/-{HALF_SPREAD}) / lot={LOT} / equity=${EQUITY:,.0f}")
    print(f"  months: {len(months)}  files: {len(files)}  OOS-filter(ts>={IS_END.date()}): {is_full_oos}")
    print("=" * 92)

    ea    = _scan_month(files, "ea",    oos_only=is_full_oos)
    ideal = _scan_month(files, "ideal", oos_only=is_full_oos)
    s_ea    = _stats(ea, with_dollars=True)
    s_ideal = _stats(ideal)

    def line(tag, s, extra=""):
        print(f"  {tag:<22} n={s.get('n',0):>3}  win={s.get('win_pct','-'):>5}%  "
              f"sumR={s.get('sum_R','-'):>8}  E[R]={s.get('E_R','-'):>8}  "
              f"t={s.get('t_stat','-')}{extra}")

    print("\nRESULTS (same span, same ticks, same config):")
    line("EA-faithful (bid/ask)", s_ea, f"  net=${s_ea.get('net_usd','-')}")
    line("Python idealized (mid+tol)", s_ideal)

    # divergence between the two fill models = the question Fork A exists to answer
    d_sumR = (s_ea.get("sum_R") or 0) - (s_ideal.get("sum_R") or 0)
    print(f"\nfill-model divergence (EA - ideal): dSumR={d_sumR:+.2f}  "
          f"dWin={ (s_ea.get('win_pct') or 0)-(s_ideal.get('win_pct') or 0):+.1f}pp")

    # verdict: is the EDGE real under faithful bid/ask fills?
    ea_pos = (s_ea.get("sum_R") or 0) > 0 and (s_ea.get("t_stat") or 0) > 2
    print("\n" + "=" * 92)
    if is_full_oos:
        if ea_pos:
            print("VERDICT: EA-faithful fills hold POSITIVE across full OOS -> ORB-001 edge is REAL.")
            print("  -> Gate-7 fidelity PASS: port is faithful AND the edge survives realistic fills.")
        else:
            print("VERDICT: EA-faithful fills do NOT clear +edge (t<=2 or sumR<=0) across full OOS.")
            print("  -> ORB-001 edge is fragile/absent under realistic no-tolerance bid/ask fills.")
    else:
        neg = (s_ea.get("net_usd") or 0) < 0
        print(f"SINGLE-MONTH ({span}): EA net=${s_ea.get('net_usd')} | ideal sumR={s_ideal.get('sum_R')}"
              f" | both {'AGREE negative' if neg else 'differ'} -> fidelity, not edge, tested here.")
    print("=" * 92)

    summary = {"model": "ORB-001", "analysis": "fork_a_ea_emulation", "span": span,
               "months": len(months), "oos_filter": is_full_oos,
               "config": {"anchor_hour": ANCHOR_HOUR, "n_minutes": N_MINUTES,
                          "half_spread": HALF_SPREAD, "lot": LOT, "equity": EQUITY},
               "ea_faithful": s_ea, "python_idealized": s_ideal,
               "fill_divergence_sumR": round(d_sumR, 2),
               "edge_survives_faithful_fills": bool(ea_pos) if is_full_oos else None}
    (_OUT / f"{tag_out}_summary.json").write_text(json.dumps(summary, indent=2, default=str),
                                                  encoding="utf-8")
    pd.DataFrame(ea).to_csv(_OUT / f"{tag_out}_ea_trades.csv", index=False, encoding="utf-8")
    pd.DataFrame(ideal).to_csv(_OUT / f"{tag_out}_ideal_trades.csv", index=False, encoding="utf-8")
    print(f"\nOutputs -> {_OUT}/{tag_out}_summary.json")


if __name__ == "__main__":
    main()
