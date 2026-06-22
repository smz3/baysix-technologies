from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from research.code.arctic_io import daily_bars

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_backtest import run_backtest_multi, edge_stats

OR_MIN      = 5
TARGET_R    = 3.0
SPREAD      = 2.0 * 0.10
IS_END      = pd.Timestamp("2024-05-02")
BASE_REPRO  = 0.3114
_OUT        = REPO / "research" / "outputs" / "orb" / "regime_gate"
OOS_MONTHS  = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]
SMA_WINDOWS = [200, 50]


def build_daily_close() -> 'pd.Series':
    """Full sorted IS+OOS daily mid-close from the Arctic daily symbol. Replaces the
    old IS-parquet + OOS-stitched-from-unsorted-ticks path (task 51): daily_bars() is
    sorted-correct end to end, so the daily CLOSE is the true chronological last tick."""
    close = daily_bars(columns=["close"])["close"].copy()
    close.index = pd.to_datetime(close.index)
    close.index.name = "date"
    d0, d1 = close.index.min().date(), close.index.max().date()
    print(f"  Daily close (Arctic): {d0} -> {d1}  ({len(close)} days)")
    return close


def compute_regime(close: 'pd.Series', window: int) -> 'pd.Series':
    sma     = close.rolling(window, min_periods=window).mean().shift(1)
    slope   = sma.diff(1)
    prev_px = close.shift(1)
    up      = (prev_px > sma) & (slope > 0)
    down    = (prev_px < sma) & (slope < 0)
    regime  = pd.Series("flat", index=close.index, name=f"regime_{window}d")
    regime[up]   = "up"
    regime[down] = "down"
    return regime


def attach_regimes(trades: 'pd.DataFrame', regime_df: 'pd.DataFrame') -> 'pd.DataFrame':
    trade_dates = pd.to_datetime(trades["date"])
    joined = trades.copy()
    joined.index = range(len(joined))
    for col in regime_df.columns:
        all_idx = regime_df[col].index.union(trade_dates)
        reg_ff  = regime_df[col].reindex(all_idx).ffill()
        joined[col] = reg_ff.reindex(trade_dates).values
    return joined


def bucket_stats(trades: 'pd.DataFrame', regime_col: str, period_label: str) -> list:
    rows = []
    for regime in ("up", "flat", "down"):
        g = trades[trades[regime_col] == regime]
        n = len(g)
        if n == 0:
            rows.append({"period": period_label, "regime_col": regime_col,
                         "regime": regime, "n": 0, "E_R": None, "sd_R": None,
                         "SE_R": None, "t_stat": None, "win_rate": None, "low_power": True})
            continue
        R    = g["R"].values
        mean = float(R.mean())
        sd   = float(R.std(ddof=1)) if n > 1 else None
        se   = sd / np.sqrt(n) if sd is not None else None
        t    = mean / se if (se is not None and se > 0) else None
        wr   = float((g["outcome"] == "target").mean())
        rows.append({"period": period_label, "regime_col": regime_col,
                     "regime": regime, "n": n,
                     "E_R":      round(mean, 4),
                     "sd_R":     round(sd,   4) if sd is not None else None,
                     "SE_R":     round(se,   4) if se is not None else None,
                     "t_stat":   round(t,    2) if t  is not None else None,
                     "win_rate": round(wr,   4),
                     "low_power": n < 50})
    return rows


def assess_trend_beta(all_rows: list) -> str:
    """Trend-beta = the edge is just long exposure to gold's secular uptrend.
    If true: edge concentrates in UP and dies/reverses in flat+down.
    Falsified if: edge stays positive+significant OUTSIDE uptrend, especially down.

    NOTE: at 200d the OOS holdout (2024-05 -> 2026) is regime-degenerate -- gold
    was in a 200d-uptrend the entire window, so OOS-200d has ~0 non-up days and
    is uninformative for this test. Evidence comes from (a) the full IS cross-
    section and (b) the 50d OOS down bucket, which DOES contain non-uptrend days.
    Do NOT call the whole study 'inconclusive' just because OOS-200d is degenerate."""
    def get(rows, period, rcol, regime, field):
        for r in rows:
            if r["period"] == period and r["regime_col"] == rcol and r["regime"] == regime:
                return r.get(field)
        return None

    def sig(period, rcol, regime, min_n=30):
        t = get(all_rows, period, rcol, regime, "t_stat")
        n = get(all_rows, period, rcol, regime, "n") or 0
        er = get(all_rows, period, rcol, regime, "E_R")
        return (t is not None) and (t >= 2.0) and (n >= min_n) and (er is not None and er > 0)

    # IS cross-section (200d): the period that actually contains up/flat/down
    is_up_er = get(all_rows, "IS", "regime_200d", "up",   "E_R")
    is_dn_er = get(all_rows, "IS", "regime_200d", "down", "E_R")
    is_up = sig("IS", "regime_200d", "up")
    is_fl = sig("IS", "regime_200d", "flat")
    is_dn = sig("IS", "regime_200d", "down")

    # OOS non-uptrend test must come from 50d (200d-OOS has no non-up days)
    oos_dn_50  = sig("OOS", "regime_50d", "down")
    oos_dn_n   = get(all_rows, "OOS", "regime_50d", "down", "n") or 0
    oos_dn_er  = get(all_rows, "OOS", "regime_50d", "down", "E_R")

    is_survives_nonup = is_fl and is_dn
    is_down_ge_up     = (is_dn_er is not None and is_up_er is not None and is_dn_er >= is_up_er)

    if is_survives_nonup and oos_dn_50:
        extra = " IS down-trend edge >= up-trend (opposite of trend-beta)." if is_down_ge_up else ""
        return ("TREND-BETA FALSIFIED: edge is positive+significant in IS up/flat/DOWN, and survives"
                f" OOS 50d down-trend (E[R]={oos_dn_er:+.3f}, n={oos_dn_n})." + extra +
                " A long-drift beta would die outside uptrends; this does the opposite."
                " Base symmetric edge is REGIME-AGNOSTIC. (200d-OOS degenerate: all up, uninformative.)")

    if is_survives_nonup and not oos_dn_50:
        return ("LIKELY TREND-INDEPENDENT (IS-strong): edge positive+significant in IS up/flat/down,"
                f" but OOS 50d down underpowered (n={oos_dn_n}). Trend-beta not supported on IS;"
                " OOS non-uptrend confirmation is thin -- revisit as holdout grows.")

    if is_up and not (is_fl or is_dn):
        return ("TREND-BETA SUPPORTED: IS edge concentrates in up-trend, absent in flat/down."
                " Forward edge should be discounted toward the non-uptrend average.")

    return ("INCONCLUSIVE: IS flat/down t-stats mixed; cannot cleanly confirm or deny trend-beta."
            " Inspect the per-bucket table directly.")


def _fmt(v, fmt: str) -> str:
    if v is None:
        return "  n/a"
    return format(v, fmt)


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 88)
    print("ORB-001 REGIME GATE (task 5) | trend-beta diagnostic | 200d + 50d SMA")
    print("=" * 88)

    print("\n[1/4] IS backtest (frozen N=5, 3R, 2-pip)...")
    is_trades = run_backtest_multi(
        None, n_list=[OR_MIN], is_only=True,
        spread_price=SPREAD, target_R=TARGET_R
    )[OR_MIN]

    ctrl    = float(is_trades["R"].mean())
    ctrl_ok = abs(ctrl - BASE_REPRO) < 0.01
    status  = "OK" if ctrl_ok else "*** MISMATCH - STOP ***"
    print(f"\n  >>> CONTROL REPRO: IS E[R] = {ctrl:+.4f}  (target {BASE_REPRO:+.4f})  {status}")
    if not ctrl_ok:
        sys.exit(1)

    print("\n[2/4] OOS backtest (sealed 2024-05-02 -> 2026)...")
    oos_trades = run_backtest_multi(
        OOS_MONTHS, n_list=[OR_MIN], is_only=False,
        spread_price=SPREAD, target_R=TARGET_R, oos_only=True
    )[OR_MIN]
    oos_er = float(oos_trades["R"].mean())
    print(f"  OOS pooled E[R] = {oos_er:+.4f}  n={len(oos_trades)}")

    print("\n[3/4] Building daily close...")
    close = build_daily_close()

    regime_df = pd.DataFrame(index=close.index)
    for w in SMA_WINDOWS:
        regime_df[f"regime_{w}d"] = compute_regime(close, w)

    print("\n  Regime label distribution (full 2016-2026 history):")
    for c in regime_df.columns:
        vc = regime_df[c].value_counts()
        up_n   = vc.get("up",   0)
        flat_n = vc.get("flat", 0)
        down_n = vc.get("down", 0)
        print(f"    {c}: up={up_n}  flat={flat_n}  down={down_n}")

    is_trades_r  = attach_regimes(is_trades,  regime_df)
    oos_trades_r = attach_regimes(oos_trades, regime_df)

    r200_is  = is_trades_r["regime_200d"].value_counts().to_dict()
    r200_oos = oos_trades_r["regime_200d"].value_counts().to_dict()
    print("\n  IS trade regime dist (200d): ",  r200_is)
    print("  OOS trade regime dist (200d):", r200_oos)

    print("\n[4/4] Per-bucket statistics...")
    all_rows: list = []
    for w in SMA_WINDOWS:
        col = f"regime_{w}d"
        all_rows += bucket_stats(is_trades_r,  col, "IS")
        all_rows += bucket_stats(oos_trades_r, col, "OOS")

    print("\n" + "=" * 88)
    for w in SMA_WINDOWS:
        col = f"regime_{w}d"
        print(f"\n--- {w}d SMA regime split ---")
        print("  Period  Regime     n    E[R]     SE_R    t_stat  win_rate")
        print("  " + "-" * 58)
        for period in ("IS", "OOS"):
            for r in all_rows:
                if r["period"] != period or r["regime_col"] != col:
                    continue
                flag = "  *** LOW n (n<50, t unreliable)" if r["low_power"] else ""
                t_s  = _fmt(r["t_stat"],   "+.2f")
                er_s = _fmt(r["E_R"],      "+.4f")
                se_s = _fmt(r["SE_R"],     "+.4f")
                wr_s = _fmt(r["win_rate"],  ".1%")
                reg  = r["regime"]
                n_v  = r["n"]
                print(f"  {period:<5} {reg:<6} {n_v:>6}  {er_s:<9} {se_s:<8} {t_s:<8} {wr_s:<9}{flag}")

    verdict = assess_trend_beta(all_rows)
    print("\n" + "=" * 88)
    print("TREND-BETA VERDICT:")
    print(f"  {verdict}")
    print("=" * 88)

    df_all = pd.DataFrame(all_rows)
    df_200 = df_all[df_all["regime_col"] == "regime_200d"].drop(columns="regime_col")
    df_50  = df_all[df_all["regime_col"] == "regime_50d"].drop(columns="regime_col")
    df_200.to_csv(_OUT / "regime_gate_200d.csv", index=False)
    df_50.to_csv( _OUT / "regime_gate_50d.csv",  index=False)

    sma_rule = ("UP: prev_close > SMA(N, shift1) AND slope > 0; "
                "DOWN: prev_close < SMA(N, shift1) AND slope < 0; "
                "FLAT: mixed. SMA + close both shift(1) -- causal, no look-ahead.")
    summary = {
        "model":    "ORB-001",
        "analysis": "regime_gate_task5",
        "control_repro": {"IS_E_R": ctrl, "target": BASE_REPRO, "ok": ctrl_ok},
        "OOS_pooled_E_R": oos_er, "OOS_n": len(oos_trades), "IS_n": len(is_trades),
        "sma_rule":    sma_rule,
        "sma_windows": SMA_WINDOWS,
        "buckets":  all_rows,
        "verdict":  verdict,
    }
    (_OUT / "regime_gate_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
        colors        = {"up": "#2e7d32", "flat": "#f9a825", "down": "#c62828"}
        regimes_order = ["up", "flat", "down"]
        col           = "regime_200d"

        for ax, period in zip(axes, ["IS", "OOS"]):
            sub  = [r for r in all_rows if r["period"] == period and r["regime_col"] == col]
            vals = [r["E_R"]  if r["E_R"]  is not None else 0.0 for r in sub]
            errs = [r["SE_R"] if r["SE_R"] is not None else 0.0 for r in sub]
            ns   = [r["n"] for r in sub]
            cls  = [colors[r["regime"]] for r in sub]
            bars = ax.bar(regimes_order, vals, yerr=errs, capsize=5, color=cls, alpha=0.88)
            ax.axhline(0, color="black", lw=0.8)
            for bar, n_val in zip(bars, ns):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        max(bar.get_height(), 0) + 0.015,
                        f"n={n_val}", ha="center", va="bottom", fontsize=8)
            ref_er = ctrl if period == "IS" else oos_er
            ax.set_title(f"{period} (pooled E[R]={ref_er:+.4f}R) -- 200d SMA")
            ax.set_ylabel("E[R] per trade (R)")
            ax.set_xlabel("Trend regime")

        fig.suptitle("ORB-001 regime gate (task 5) -- edge by gold trend regime", fontsize=12)
        fig.tight_layout()
        fig.savefig(_OUT / "regime_gate.png", dpi=120)
        print(f"\nPlot -> {_OUT}")
    except Exception as e:
        print(f"  Plot skipped ({e})")

    print(f"\nOutputs -> {_OUT}")
    print("  regime_gate_200d.csv")
    print("  regime_gate_50d.csv")
    print("  regime_gate_summary.json")
    print("  regime_gate.png")


if __name__ == "__main__":
    main()
