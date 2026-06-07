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
