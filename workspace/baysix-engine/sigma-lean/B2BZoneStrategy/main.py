"""
B2B Zone Strategy — LEAN QCAlgorithm (SAMTC V6.7)
==================================================
Implements the full SAMTC (State Aware Multi Temporal Consensus) architecture
inside a QuantConnect / LEAN event-driven framework.

Architecture
------------
- Security  : BTCUSDT  |  Binance  |  H1 resolution (primary entry TF)
- Detection : sigma_core detect_swings() + detect_b2b_zones() on rolling 500-bar window
              across H1 (live), H4, D1, W1, MN1 (via LEAN Consolidators)
- Narrative : StrategyOrchestrator (V6.7) maintains FlowState + Storyline Latches
              for all 6 timeframes (MN1 → W1 → D1 → H4 → H1 → M30)
- Gate A    : Anti-trend Faders — only at major HTF Magnet cores
- Gate B    : Inertial Flow Continuation — liberated entry aligned with D1 latch
- Gate C    : Discovery Bridge — local leadership when HTF is invalid but latch confluent
- Entry     : T2 (50% touch) or T3 (L2 touch) on H1 — T1 is muted by Tier Gating
- Exit      : SL at L2 + 0.3% buffer  |  TP at 2R (planned RR = 2.0)
- Sizing    : 1% portfolio risk per trade

Zone lifecycle
--------------
Zones are re-detected every bar on the full history window.
Active zone status (T1/T2/T3 touch progression + invalidation) is tracked via
update_active_zones() from zone_status.py.
Orchestrator flow state is updated on every H1 bar using all-TF zone lists.
Trade failures are reported back to EfficiencyGovernor for Structural Memory.
"""

# ── LEAN standard import ──────────────────────────────────────────────────────
from AlgorithmImports import *

# ── sigma_core import (workspace root mounted at /LeanCLI in Docker) ──────────
import sys
import os

for candidate in ["/LeanCLI", os.path.dirname(__file__), "."]:
    if os.path.isdir(os.path.join(candidate, "sigma_core")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
        break

from sigma_core.b2b.detectors.swing_points import detect_swings
from sigma_core.b2b.detectors.b2b_engine import detect_b2b_zones
from sigma_core.b2b.detectors.zone_status import update_active_zones
from sigma_core.b2b.models.structures import (
    SignalDirection, DetectionConfig, B2BZoneInfo,
)
from sigma_core.b2b.strategy.orchestrator import StrategyOrchestrator

import pandas as pd
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, List


# ─────────────────────────────────────────────────────────────────────────────
# Config constants
# ─────────────────────────────────────────────────────────────────────────────
SYMBOL          = "BTCUSDT"
MARKET          = Market.Binance
RESOLUTION      = Resolution.Hour    # H1 bars from single flat hour/ ZIP — fast I/O
TIMEFRAME_LABEL = "H1"

HISTORY_BARS    = 500      # rolling window fed to sigma_core per-TF
MIN_BARS        = 200      # minimum bars before we start trading
RISK_PCT        = 0.01     # 1% of portfolio risked per trade
PLANNED_RR      = 2.0      # take-profit at 2R
SL_BUFFER_PCT   = 0.003    # 0.3% beyond L2 for SL to avoid wick stops
REDETECT_EVERY  = 1        # re-run zone detection every H1 bar


# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ActiveTrade:
    """Tracks the current open position."""
    zone_id:   str
    direction: SignalDirection
    entry_px:  float
    sl_px:     float
    tp_px:     float
    risk_pts:  float


# ─────────────────────────────────────────────────────────────────────────────
class B2BZoneStrategy(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2022, 12, 31)
        self.SetCash(100_000)

        # ── Security ──────────────────────────────────────────────────────────
        self._crypto = self.AddCrypto(SYMBOL, RESOLUTION, MARKET)
        self._crypto.SetDataNormalizationMode(DataNormalizationMode.Raw)
        self.SetBenchmark(self._crypto.Symbol)

        # ── sigma_core detection config ───────────────────────────────────────
        self._detect_cfg = DetectionConfig(
            swing_window=3,
            swing_lookback=20,
            max_breakout_age=0,
            historical_bars=HISTORY_BARS,
            min_age_bars=8,
            max_zone_age_bars=5000,
        )

        # ── H1 state (primary entry TF) ──────────────────────────────────────
        self._h1_buffer: List[dict]            = []   # rolling H1 bar history
        self._active_zones: List[B2BZoneInfo]  = []   # H1 zones
        self._traded_zone_ids: set             = set()
        self._active_trade: Optional[ActiveTrade] = None
        self._bar_count: int                   = 0

        # ── Multi-timeframe bar buffers ───────────────────────────────────────
        self._h4_buffer:  List[dict] = []
        self._d1_buffer:  List[dict] = []
        self._w1_buffer:  List[dict] = []
        self._mn1_buffer: List[dict] = []

        # ── Multi-timeframe zone lists ────────────────────────────────────────
        self._h4_zones:  List[B2BZoneInfo] = []
        self._d1_zones:  List[B2BZoneInfo] = []
        self._w1_zones:  List[B2BZoneInfo] = []
        self._mn1_zones: List[B2BZoneInfo] = []

        # ── SAMTC Orchestrator ────────────────────────────────────────────────
        self._orchestrator = StrategyOrchestrator(symbol=SYMBOL)

        # ── LEAN Consolidators (all derived from H1 primary) ─────────────────
        symbol = self._crypto.Symbol
        self.Consolidate(symbol, timedelta(hours=4),  self._on_h4_bar)   # H4  = 4 × H1
        self.Consolidate(symbol, timedelta(days=1),   self._on_d1_bar)   # D1  = 24 × H1
        self.Consolidate(symbol, timedelta(weeks=1),  self._on_w1_bar)   # W1  = 168 × H1
        self.Consolidate(symbol, timedelta(days=30),  self._on_mn1_bar)  # MN1 approx

        # Warm up with 3000 H1 bars (~125 days — enough for MN1 context)
        self.SetWarmUp(3000, RESOLUTION)

        self.Debug(f"B2BZoneStrategy (SAMTC V6.7) initialized — {SYMBOL} {TIMEFRAME_LABEL}")

    # ─────────────────────────────────────────────────────────────────────────
    # HTF Consolidator handlers
    # ─────────────────────────────────────────────────────────────────────────
    def _on_h4_bar(self, bar) -> None:
        self._h4_buffer.append({
            "time":  bar.EndTime,
            "open":  float(bar.Open),
            "high":  float(bar.High),
            "low":   float(bar.Low),
            "close": float(bar.Close),
        })
        if len(self._h4_buffer) > HISTORY_BARS:
            self._h4_buffer.pop(0)
        if not self.IsWarmingUp and len(self._h4_buffer) >= 20:
            self._h4_zones = self._detect_zones_for_tf(self._h4_buffer, "H4")

    def _on_d1_bar(self, bar) -> None:
        self._d1_buffer.append({
            "time":  bar.EndTime,
            "open":  float(bar.Open),
            "high":  float(bar.High),
            "low":   float(bar.Low),
            "close": float(bar.Close),
        })
        if len(self._d1_buffer) > HISTORY_BARS:
            self._d1_buffer.pop(0)
        if not self.IsWarmingUp and len(self._d1_buffer) >= 20:
            self._d1_zones = self._detect_zones_for_tf(self._d1_buffer, "D1")

    def _on_w1_bar(self, bar) -> None:
        self._w1_buffer.append({
            "time":  bar.EndTime,
            "open":  float(bar.Open),
            "high":  float(bar.High),
            "low":   float(bar.Low),
            "close": float(bar.Close),
        })
        if len(self._w1_buffer) > HISTORY_BARS:
            self._w1_buffer.pop(0)
        if not self.IsWarmingUp and len(self._w1_buffer) >= 20:
            self._w1_zones = self._detect_zones_for_tf(self._w1_buffer, "W1")

    def _on_mn1_bar(self, bar) -> None:
        self._mn1_buffer.append({
            "time":  bar.EndTime,
            "open":  float(bar.Open),
            "high":  float(bar.High),
            "low":   float(bar.Low),
            "close": float(bar.Close),
        })
        if len(self._mn1_buffer) > HISTORY_BARS:
            self._mn1_buffer.pop(0)
        if not self.IsWarmingUp and len(self._mn1_buffer) >= 20:
            self._mn1_zones = self._detect_zones_for_tf(self._mn1_buffer, "MN1")

    # ─────────────────────────────────────────────────────────────────────────
    def _detect_zones_for_tf(self, buffer: List[dict], tf_label: str) -> List[B2BZoneInfo]:
        """Run sigma_core B2B detection on a given TF bar buffer."""
        try:
            df = pd.DataFrame(buffer)
            df["time"] = pd.to_datetime(df["time"])
            swings = detect_swings(df, config=self._detect_cfg)
            if not swings:
                return []
            return detect_b2b_zones(df, swings, tf=tf_label, config=self._detect_cfg)
        except Exception as e:
            self.Debug(f"[{tf_label}] Zone detection error: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    def OnData(self, data: Slice):
        symbol = self._crypto.Symbol

        if not data.Bars.ContainsKey(symbol):
            return

        bar = data.Bars[symbol]

        # Accumulate bar into rolling H1 buffer
        self._h1_buffer.append({
            "time":  bar.EndTime,
            "open":  float(bar.Open),
            "high":  float(bar.High),
            "low":   float(bar.Low),
            "close": float(bar.Close),
        })
        if len(self._h1_buffer) > HISTORY_BARS:
            self._h1_buffer.pop(0)

        self._bar_count += 1

        # Need enough history before trading
        if self.IsWarmingUp or self._bar_count < MIN_BARS:
            return

        # ── Manage existing position ──────────────────────────────────────────
        if self._active_trade is not None:
            self._manage_exit(bar)
            return  # one trade at a time

        # ── Re-detect H1 zones every REDETECT_EVERY bars ─────────────────────
        if self._bar_count % REDETECT_EVERY == 0:
            self._run_detection()

        # ── Update active H1 zone statuses (touch progression + invalidation) ─
        current_time = pd.Timestamp(bar.EndTime)
        update_active_zones(
            current_low   = float(bar.Low),
            current_high  = float(bar.High),
            current_close = float(bar.Close),
            current_time  = current_time,
            active_zones  = self._active_zones,
        )

        # Prune invalidated zones
        self._active_zones = [z for z in self._active_zones if z.is_valid]

        # ── Update SAMTC orchestrator flow state ──────────────────────────────
        all_tf_zones = {
            "H1":  self._active_zones,
            "H4":  self._h4_zones,
            "D1":  self._d1_zones,
            "W1":  self._w1_zones,
            "MN1": self._mn1_zones,
        }
        self._orchestrator.update_flow_state(
            all_tf_zones,
            float(bar.Close),
            current_time,
        )

        # ── Look for entries ──────────────────────────────────────────────────
        self._check_entry(bar)

    # ─────────────────────────────────────────────────────────────────────────
    def _run_detection(self):
        """Run sigma_core B2B detection on the current H1 bar buffer."""
        if len(self._h1_buffer) < MIN_BARS:
            return

        df = pd.DataFrame(self._h1_buffer)
        df["time"] = pd.to_datetime(df["time"])

        swings = detect_swings(df, config=self._detect_cfg)
        if not swings:
            return

        zones = detect_b2b_zones(df, swings, tf=TIMEFRAME_LABEL, config=self._detect_cfg)

        # Merge new zones into active set (deduplicate by zone_id)
        existing_ids = {z.zone_id for z in self._active_zones}
        added = 0
        for z in zones:
            if z.zone_id not in existing_ids and z.zone_id not in self._traded_zone_ids:
                self._active_zones.append(z)
                existing_ids.add(z.zone_id)
                added += 1

        if added > 0:
            self.Debug(f"[{self.Time}] Detected {len(zones)} zones, {added} new  "
                       f"| active={len(self._active_zones)}")

    # ─────────────────────────────────────────────────────────────────────────
    def _check_entry(self, bar):
        """
        SAMTC V6.7 Entry Gate.

        Determines touch progression on this bar (T1/T2/T3) and delegates to the
        orchestrator's is_trade_allowed() for Gate A / Gate B / Gate C validation.

        Tier Gating on H1: T1 is muted — entry requires T2 (50% touch) or T3 (L2 touch).

        Buy zone  (BULLISH): bar.Low  <= zone.L1_price (T1), <= zone.fifty_percent (T2), <= zone.L2_price (T3)
        Sell zone (BEARISH): bar.High >= zone.L1_price (T1), >= zone.fifty_percent (T2), >= zone.L2_price (T3)
        """
        close_px = float(bar.Close)
        low_px   = float(bar.Low)
        high_px  = float(bar.High)

        for zone in self._active_zones:
            if not zone.is_valid:
                continue
            if zone.zone_id in self._traded_zone_ids:
                continue

            # Determine which touch level was reached on THIS bar
            trigger_type = None

            if zone.direction == SignalDirection.BULLISH:
                if low_px <= zone.L2_price and close_px > zone.L2_price:
                    trigger_type = "T3"   # L2 touched (deepest)
                elif low_px <= zone.fifty_percent and close_px > zone.L2_price:
                    trigger_type = "T2"   # 50% touched
                elif low_px <= zone.L1_price and close_px > zone.L2_price:
                    trigger_type = "T1"   # L1 touched (shallowest)

            elif zone.direction == SignalDirection.BEARISH:
                if high_px >= zone.L2_price and close_px < zone.L2_price:
                    trigger_type = "T3"   # L2 touched (deepest)
                elif high_px >= zone.fifty_percent and close_px < zone.L2_price:
                    trigger_type = "T2"   # 50% touched
                elif high_px >= zone.L1_price and close_px < zone.L2_price:
                    trigger_type = "T1"   # L1 touched (shallowest)

            if trigger_type is None:
                continue

            current_time = pd.Timestamp(bar.EndTime)

            # ── SAMTC Gatekeeper ─────────────────────────────────────────────
            allowed, reason, _, _ = self._orchestrator.is_trade_allowed(
                signal_tf     = TIMEFRAME_LABEL,
                direction     = zone.direction,
                zone          = zone,
                current_price = close_px,
                current_time  = current_time,
                trigger_type  = trigger_type,
            )

            if not allowed:
                self.Debug(
                    f"[{self.Time}] BLOCKED [{trigger_type}] {zone.direction.value} "
                    f"zone={zone.zone_id}  reason={reason}"
                )
                continue

            # ── Sizing ────────────────────────────────────────────────────────
            entry_px = close_px
            if zone.direction == SignalDirection.BULLISH:
                sl_px = zone.L2_price * (1.0 - SL_BUFFER_PCT)
                tp_px = entry_px + PLANNED_RR * (entry_px - sl_px)
            else:
                sl_px = zone.L2_price * (1.0 + SL_BUFFER_PCT)
                tp_px = entry_px - PLANNED_RR * (sl_px - entry_px)

            risk_pts = abs(entry_px - sl_px)
            if risk_pts <= 0:
                continue

            portfolio_value = float(self.Portfolio.TotalPortfolioValue)
            risk_dollars    = portfolio_value * RISK_PCT
            quantity        = risk_dollars / risk_pts

            symbol = self._crypto.Symbol

            if zone.direction == SignalDirection.BULLISH:
                self.MarketOrder(symbol, quantity)
            else:
                self.MarketOrder(symbol, -quantity)

            self._active_trade = ActiveTrade(
                zone_id   = zone.zone_id,
                direction = zone.direction,
                entry_px  = entry_px,
                sl_px     = sl_px,
                tp_px     = tp_px,
                risk_pts  = risk_pts,
            )
            self._traded_zone_ids.add(zone.zone_id)

            self.Log(
                f"[ENTRY] {zone.direction.value} [{trigger_type}]  reason={reason}  "
                f"entry={entry_px:.2f}  sl={sl_px:.2f}  tp={tp_px:.2f}  qty={quantity:.6f}  "
                f"zone={zone.zone_id}  L1={zone.L1_price:.2f}  L2={zone.L2_price:.2f}"
            )
            break  # one entry per bar

    # ─────────────────────────────────────────────────────────────────────────
    def _manage_exit(self, bar):
        """Check SL and TP conditions for the current open trade."""
        if self._active_trade is None:
            return

        trade    = self._active_trade
        low_px   = float(bar.Low)
        high_px  = float(bar.High)
        symbol   = self._crypto.Symbol

        hit_sl = False
        hit_tp = False
        exit_reason = ""

        if trade.direction == SignalDirection.BULLISH:
            if low_px  <= trade.sl_px: hit_sl = True; exit_reason = "SL"
            if high_px >= trade.tp_px: hit_tp = True; exit_reason = "TP"
        else:
            if high_px >= trade.sl_px: hit_sl = True; exit_reason = "SL"
            if low_px  <= trade.tp_px: hit_tp = True; exit_reason = "TP"

        if hit_sl or hit_tp:
            self.Liquidate(symbol)
            exit_px = trade.sl_px if hit_sl else trade.tp_px
            pnl_pts = (exit_px - trade.entry_px) if trade.direction == SignalDirection.BULLISH \
                      else (trade.entry_px - exit_px)
            rr = pnl_pts / trade.risk_pts if trade.risk_pts > 0 else 0.0

            self.Log(
                f"[EXIT-{exit_reason}]  entry={trade.entry_px:.2f}  "
                f"exit≈{exit_px:.2f}  RR={rr:.2f}R  zone={trade.zone_id}"
            )

            # Report failure to orchestrator's Structural Memory
            if hit_sl:
                self._orchestrator.report_trade_failure(
                    TIMEFRAME_LABEL,
                    trade.direction,
                    pd.Timestamp(bar.EndTime),
                )

            self._active_trade = None

    # ─────────────────────────────────────────────────────────────────────────
    def OnOrderEvent(self, orderEvent: OrderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.Debug(f"Order filled: {orderEvent}")

    def OnEndOfAlgorithm(self):
        zones_traded = len(self._traded_zone_ids)
        self.Log(f"Backtest complete — zones traded: {zones_traded}")
        self.Log(f"Final portfolio value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
