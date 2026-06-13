"""
ORB-004 Gate 3 — "Does the dumb rule have any edge, raw AND after costs?"

The filters ARE the hypothesis (the unconditional breakout is a clean null, ORB-001
result_id 122). So Gate 3 sweeps them and measures what each buys:
    vwap_on in {False, True}   x   regime-k in {0, 1.0, 1.25, 1.5}
on the FULL IS history, raw (spread=0) and net (JM 2-pip = 0.20 price, half-spread
barrier shift). E_R per-trade + t-stat, POOLED and PER-SESSION (the kill condition
needs the per-session view — a dead session can't hide in the pool).

Pre-registered kill-line (Gate 1):
    net pooled E[R] > 0 AND t >= 2   OR   any single session clears the same.
    Else: H0 not rejected + no session survives -> ORB-spot family CLOSED.

Headline config (the spec): net, vwap_on=True, k=1.0 -> logged via run_and_log
(fact only; verdict left for a human to stamp after reading the sweep).

Run (rule 12, visible window):
    python research/models/orb/orb004/gate3_edge.py full
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb004.orb004_core import (
    load_minute_bars, daily_atr, build_session_signals, SESSIONS, IS_END,
)
from research.code.run_and_log import run_and_log

SLICE_MONTHS = [(2019, 1), (2019, 4), (2019, 7), (2019, 10)]
SPREAD_NET = 0.20                       # JM 2 pip * $0.10/pip price-units
K_GRID = [0.0, 1.0, 1.25, 1.5]
HEADLINE = dict(vwap_on=True, k=1.0)    # the spec config


def edge_stats(df: pd.DataFrame) -> dict:
    """Per-trade E[R] + t-stat (per-period Sharpe * sqrt n) on a TAKEN subset."""
    R = df["R"].dropna().values
    n = len(R)
    if n < 2:
        return {"n": n, "E_R": np.nan, "t": np.nan, "win": np.nan}
    mean, sd = float(R.mean()), float(R.std(ddof=1))
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    win = float((R > 0).mean())
    return {"n": n, "E_R": mean, "t": t, "win": win}


def take(sig: pd.DataFrame, vwap_on: bool, k: float) -> pd.DataFrame:
    """Apply a filter config -> the trades it admits."""
    m = sig["direction"] != "none"
    if vwap_on:
        m &= sig["vwap_aligned"]
    if k > 0:
        m &= sig["range_w_regime"] >= k        # NaN (warm-up) excluded when gated
    return sig[m]


def sweep(sig: pd.DataFrame, tag: str) -> None:
    print(f"\n===== SWEEP ({tag}) =====")
    print(f"{'vwap':<5} {'k':>5} {'scope':<7} {'n':>5} {'E_R':>9} {'t':>7} {'win':>6}")
    for vwap_on in (False, True):
        for k in K_GRID:
            taken = take(sig, vwap_on, k)
            s = edge_stats(taken)
            print(f"{str(vwap_on):<5} {k:>5} {'POOL':<7} {s['n']:>5} "
                  f"{s['E_R']:>+9.4f} {s['t']:>+7.2f} {s['win']:>6.1%}")
            for sess in SESSIONS:
                ss = edge_stats(taken.xs(sess, level="session") if len(taken) else taken)
                print(f"{'':<5} {'':>5} {sess:<7} {ss['n']:>5} "
                      f"{ss['E_R']:>+9.4f} {ss['t']:>+7.2f} {ss['win']:>6.1%}")


def main(mode: str) -> None:
    year_months = SLICE_MONTHS if mode == "slice" else None      # full/report = all IS
    print("=" * 72)
    print(f"ORB-004 GATE 3  |  mode={mode}  |  XAUUSD  |  multi-session VWAP/ATR ORB")
    print("=" * 72)

    bars = load_minute_bars(year_months, is_only=True)
    atr = daily_atr(14)
    sig_raw = build_session_signals(bars, atr, spread_price=0.0)
    sig_net = build_session_signals(bars, atr, spread_price=SPREAD_NET)

    sweep(sig_raw, "RAW  spread=0")
    sweep(sig_net, f"NET  spread={SPREAD_NET}")

    # headline = spec config, NET -> log the fact (verdict opt-in, human reads first)
    taken = take(sig_net, **HEADLINE)
    s = edge_stats(taken)
    print(f"\n----- HEADLINE (net, vwap_on={HEADLINE['vwap_on']}, k={HEADLINE['k']}) -----")
    print(f"  pooled: n={s['n']}  E_R={s['E_R']:+.4f}  t={s['t']:+.2f}  win={s['win']:.1%}")

    d0, d1 = str(bars.index.min().date()), str(bars.index.max().date())

    def runner():
        return {
            "stage": "IS", "period": "per_trade", "cost_adjusted": 1,
            "n_obs": int(s["n"]), "data_start": d0, "data_end": d1,
            "metrics": {"E_R": float(s["E_R"]), "t_stat": float(s["t"])},
            "parameters": '{"vwap_on": true, "regime_k": 1.0, "spread_price": 0.20, '
                          '"exit": "sessionclose_flat", "sessions": "asian+london+ny"}',
            "notes": f"Gate-3 headline net config, full IS 1-min conservative exit; mode={mode}",
        }

    if mode == "full":
        out = run_and_log("ORB-004", runner, gate_number=3)   # fact only, verdict=None
        print(f"\n[logged] result_ids={out['result_ids']} primary={out['primary_result_id']}")
    else:
        print(f"\n[{mode} mode: not logged]")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "slice"
    if mode not in ("slice", "full", "report"):     # report = full IS data, no DB write
        sys.exit("usage: gate3_edge.py [slice|full|report]")
    main(mode)
