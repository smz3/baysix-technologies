"""
ORB-001 $50 dollar-equity simulator (survival test).

Edge is ALREADY proven in R-multiples (G0-G6). This converts each ORB trade's
R-multiple into REAL dollars on a $50 account and walks the balance through the
OOS slice under a survival skip-filter, to answer: can $50 survive this edge?

Dollar math (JM XAUUSD.s, brokers/justmarkets.yaml):
  contract = 100 oz/lot, min lot 0.01, lot_step 0.01.
  pnl_usd = R * range_w * 100 * lot      (range_w = 1R in price $/oz)
  On min lot 0.01: pnl_usd = R * range_w  (a -1R loss costs range_w dollars).

Costs: spread already embedded in R as a win-rate drag (do NOT re-deduct);
swap $0 (swap-free + EOD-flat); commission $0 (Pro). Spread is the only cost.

    python research/models/orb/equity_sim.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

CONTRACT_OZ = 100.0
MIN_LOT = 0.01
LEVERAGE = 3000          # JM dynamic max for XAUUSD
STOPOUT_PCT = 20.0       # equity/used_margin*100 < 20 -> stop out


def trade_pnl_usd(R: float, range_w: float, lot: float = MIN_LOT) -> float:
    """Dollar P&L of one trade. range_w = 1R in price ($/oz)."""
    return R * range_w * CONTRACT_OZ * lot


def used_margin_usd(entry_px: float, lot: float = MIN_LOT,
                    leverage: int = LEVERAGE) -> float:
    """Margin to hold the position = notional / leverage."""
    notional = entry_px * CONTRACT_OZ * lot
    return notional / leverage


def simulate_equity(trades: pd.DataFrame, start: float = 50.0,
                    lot: float = MIN_LOT, risk_cap_pct: float | None = None,
                    leverage: int = LEVERAGE) -> dict:
    """
    Walk a dollar balance through trades in date order.

    risk_cap_pct: skip a trade if its $ risk (range_w * 100 * lot) exceeds this
                  % of CURRENT equity. None = take every affordable trade.
    Blow-up: equity can no longer fund the min-lot margin (or hits <= 0).

    Returns {"curve": DataFrame, "summary": dict}.
    """
    df = trades.sort_values("date").reset_index(drop=True)
    equity = start
    peak = start
    max_dd = 0.0
    n_taken = n_skipped = 0
    streak = worst_streak = 0
    blew_up = False
    curve = []

    for _, t in df.iterrows():
        risk_usd = abs(t["range_w"]) * CONTRACT_OZ * lot
        margin = used_margin_usd(t["entry_px"], lot, leverage)

        # ruin: cannot even open the minimum position
        if equity <= 0 or equity < margin:
            blew_up = True
            break

        # survival skip-filter
        if risk_cap_pct is not None and equity > 0 and (risk_usd / equity) * 100.0 > risk_cap_pct:
            n_skipped += 1
            curve.append({"date": t["date"], "equity": equity, "action": "skip"})
            continue

        pnl = trade_pnl_usd(t["R"], t["range_w"], lot)
        equity += pnl
        n_taken += 1
        streak = streak + 1 if pnl < 0 else 0
        worst_streak = max(worst_streak, streak)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
        curve.append({"date": t["date"], "equity": equity, "action": "trade"})

        if equity <= 0:
            blew_up = True
            break

    curve_df = pd.DataFrame(curve)
    summary = {
        "start_equity": start,
        "terminal_equity": equity,
        "return_pct": (equity / start - 1.0) * 100.0,
        "max_drawdown_pct": max_dd * 100.0,
        "worst_losing_streak": worst_streak,
        "n_taken": n_taken,
        "n_skipped": n_skipped,
        "blew_up": blew_up,
        "risk_cap_pct": risk_cap_pct,
    }
    return {"curve": curve_df, "summary": summary}


def daily_returns(curve: pd.DataFrame, start: float) -> pd.Series:
    """Per-trade-day fractional returns from the equity curve (for quantstats)."""
    eq = curve[curve["action"] != "skip"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.set_index("date")["equity"]
    prev = eq.shift(1)
    prev.iloc[0] = start
    return (eq / prev - 1.0).rename("returns")


def load_oos_trades(n_minutes: int = 5, target_R: float = 3.0) -> pd.DataFrame:
    """Run the frozen ORB config on the sealed OOS slice -> trade DataFrame."""
    from research.models.orb.orb_backtest import run_backtest_multi
    months = [(y, m) for y in range(2024, 2027) for m in range(1, 13) if (y, m) >= (2024, 5)]
    runs = run_backtest_multi(months, n_list=[n_minutes], is_only=False,
                              spread_price=2.0 * 0.10, target_R=target_R, oos_only=True)
    return runs[n_minutes]


def sweep_caps(trades: pd.DataFrame, caps=(5.0, 10.0, 15.0, 20.0, None),
               start: float = 50.0) -> pd.DataFrame:
    """Run the sim across survival-cap settings; one summary row per cap."""
    rows = []
    for cap in caps:
        s = simulate_equity(trades, start=start, risk_cap_pct=cap)["summary"]
        rows.append(s)
    return pd.DataFrame(rows)


def write_outputs(curve: pd.DataFrame, start: float, out_dir: Path, tag: str) -> None:
    """quantstats tearsheet (HTML) + custom plotly equity/drawdown curve."""
    import plotly.graph_objects as go

    out_dir.mkdir(parents=True, exist_ok=True)
    rets = daily_returns(curve, start)

    try:
        import quantstats as qs
        qs.reports.html(rets, output=str(out_dir / f"orb001_equity_{tag}_tearsheet.html"),
                        title=f"ORB-001 $50 survival — {tag}")
    except Exception as e:  # quantstats can be brittle on tiny/edge series
        print(f"[warn] quantstats tearsheet skipped: {e}")

    eq = curve[curve["action"] != "skip"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    peak = eq["equity"].cummax()
    dd = (eq["equity"] - peak) / peak * 100.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq["date"], y=eq["equity"], name="Equity ($)", yaxis="y1"))
    fig.add_trace(go.Scatter(x=eq["date"], y=dd, name="Drawdown (%)", yaxis="y2",
                             line=dict(dash="dot")))
    fig.update_layout(
        title=f"ORB-001 $50 equity & drawdown — {tag}",
        yaxis=dict(title="Equity ($)"),
        yaxis2=dict(title="Drawdown (%)", overlaying="y", side="right"),
    )
    fig.write_html(str(out_dir / f"orb001_equity_{tag}_curve.html"))


def main() -> None:
    out_dir = Path(__file__).resolve().parents[3] / "research" / "outputs"
    print("=" * 84)
    print("ORB-001 $50 EQUITY SIMULATOR — OOS survival (min-lot, Mode A)")
    print("=" * 84)
    trades = load_oos_trades()
    print(f"OOS trades: {len(trades)}  ({trades['date'].min()} -> {trades['date'].max()})\n")

    sweep = sweep_caps(trades)
    cols = ["risk_cap_pct", "terminal_equity", "return_pct", "max_drawdown_pct",
            "worst_losing_streak", "n_taken", "n_skipped", "blew_up"]
    print(sweep[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # write outputs for the no-cap baseline + best surviving cap
    base = simulate_equity(trades, start=50.0, risk_cap_pct=None)
    write_outputs(base["curve"], 50.0, out_dir, tag="nocap")
    survivors = sweep[~sweep["blew_up"]].sort_values("terminal_equity", ascending=False)
    if len(survivors):
        best_cap = survivors.iloc[0]["risk_cap_pct"]
        best = simulate_equity(trades, start=50.0, risk_cap_pct=best_cap)
        write_outputs(best["curve"], 50.0, out_dir, tag=f"cap{best_cap:g}")
        print(f"\nBest surviving cap: {best_cap}%  -> terminal ${best['summary']['terminal_equity']:,.2f}")
    else:
        print("\nNo cap setting survived — $50 cannot trade this edge at min-lot.")
    print(f"\noutputs -> {out_dir}")


if __name__ == "__main__":
    main()
