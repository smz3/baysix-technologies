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
