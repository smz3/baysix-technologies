"""
Render B2B zones over the close line for the trader's-eye verification.

Faithful view: B2B is CLOSE-ONLY by doctrine, so we plot the close line exactly
as the engine sees it, with swing markers and L1-L2 zone bands on top.

Detection runs over the FULL in-sample history (so swing context is complete);
only zones created within the display window are drawn. OOS stays sealed.

Usage:
    python b2b/backtest/render_zones.py [tf] [last_n_bars]
    e.g. python b2b/backtest/render_zones.py d1 400
Output: b2b/backtest/outputs/zones_{tf}_is_last{N}.html
"""
import os
import sys

import numpy as np
import pandas as pd

# self-path so `sigma_core...` resolves (b2b/ root is two levels up)
B2B_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, B2B_ROOT)
REPO = os.path.abspath(os.path.join(B2B_ROOT, "..", ".."))   # research/

from sigma_core.b2b.models.structures import SignalDirection           # noqa: E402
from sigma_core.b2b.detectors.swing_points import detect_swings        # noqa: E402
from sigma_core.b2b.detectors.b2b_engine import detect_b2b_zones       # noqa: E402

import plotly.graph_objects as go                                      # noqa: E402

BULL = "#2ca02c"   # buy zones / lows
BEAR = "#d62728"   # sell zones / highs


def apply_close_invalidation(df, zones):
    """Replay history to mark zones INVALIDATED (B2BZoneStatus.mqh rule).

    A zone dies on the first bar AFTER creation that CLOSES beyond its stop:
        BEARISH (sell): close > max(L1, L2)
        BULLISH (buy):  close < min(L1, L2)
    Close-based, so close-only bars reproduce the live dead/alive set exactly.
    """
    closes = df["close"].values
    times = df["time"].values
    n = len(closes)
    for z in zones:
        i0 = z.created_bar_index
        if i0 is None or i0 < 0 or i0 >= n - 1:
            continue
        post = closes[i0 + 1:]
        if z.direction == SignalDirection.BEARISH:
            hits = np.where(post > max(z.L1_price, z.L2_price))[0]
        else:
            hits = np.where(post < min(z.L1_price, z.L2_price))[0]
        if len(hits):
            k = i0 + 1 + int(hits[0])
            z.is_invalidated = True
            z.is_valid = False
            z.invalidation_time = pd.Timestamp(times[k])


def main():
    tf = (sys.argv[1] if len(sys.argv) > 1 else "d1").lower()
    last_n = int(sys.argv[2]) if len(sys.argv) > 2 else 400

    bars_fp = os.path.join(REPO, "data", "parquet", "bars",
                           f"xauusd_{tf}_gmt3_bid_is.parquet")
    df = pd.read_parquet(bars_fp).sort_values("time").reset_index(drop=True)
    print(f"[render] {tf.upper()} IS bars: {len(df)}  "
          f"{df.time.min()} -> {df.time.max()}")

    # detect on full history, then replay invalidation (no ghost zones)
    swings = detect_swings(df)
    zones = detect_b2b_zones(df, swings, tf=tf.upper())
    apply_close_invalidation(df, zones)
    print(f"[render] swings={len(swings)}  zones(total)={len(zones)}  "
          f"invalidated={sum(z.is_invalidated for z in zones)}")

    win = df.tail(last_n)
    w0, w1 = win.time.min(), win.time.max()
    win_swings = [s for s in swings if w0 <= pd.Timestamp(s.time) <= w1]

    # LOCK the price axis to the visible close range so zones can never distort it
    ylo, yhi = float(win.close.min()), float(win.close.max())
    pad = (yhi - ylo) * 0.05
    ylo, yhi = ylo - pad, yhi + pad

    # a zone is alive [created -> death]; death = invalidation_time, else right edge
    def death_of(z):
        return pd.Timestamp(z.invalidation_time) if z.is_invalidated else w1

    # keep zones whose alive-span overlaps the window AND whose price band is on-screen
    def on_screen(z):
        lo, hi = min(z.L1_price, z.L2_price), max(z.L1_price, z.L2_price)
        return hi >= ylo and lo <= yhi
    win_zones = [z for z in zones
                 if pd.Timestamp(z.zone_created_time) <= w1
                 and death_of(z) >= w0 and on_screen(z)]
    print(f"[render] window: {w0} -> {w1}  swings={len(win_swings)}  "
          f"zones(visible)={len(win_zones)}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=win.time, y=win.close, mode="lines",
                             name="close", line=dict(color="#333", width=1)))

    # swing markers
    for typ, sym, col in [("HIGH", "triangle-down", BEAR), ("LOW", "triangle-up", BULL)]:
        pts = [s for s in win_swings if s.type.name == typ]
        if pts:
            fig.add_trace(go.Scatter(
                x=[s.time for s in pts], y=[s.price for s in pts],
                mode="markers", name=f"swing {typ.lower()}",
                marker=dict(symbol=sym, size=7, color=col)))

    # zone bands over their ALIVE span only: creation -> death (invalidation) or edge.
    # A bulldozed zone's band terminates where price closed through L2 (no ghosts).
    for z in win_zones:
        col = BULL if z.direction == SignalDirection.BULLISH else BEAR
        y0, y1 = sorted((z.L1_price, z.L2_price))
        x0 = max(pd.Timestamp(z.zone_created_time), w0)
        x1 = min(death_of(z), w1)
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(width=0), fillcolor=col, opacity=0.12, layer="below")
        fig.add_shape(type="line", x0=x0, x1=x1, y0=z.L1_price, y1=z.L1_price,
                      line=dict(color=col, width=1))
        fig.add_shape(type="line", x0=x0, x1=x1, y0=z.L2_price, y1=z.L2_price,
                      line=dict(color=col, width=1, dash="dot"))
        tag = f"INVALIDATED {z.invalidation_time}" if z.is_invalidated else "valid"
        fig.add_trace(go.Scatter(
            x=[x0], y=[z.L1_price], mode="markers",
            marker=dict(symbol="circle", size=5, color=col), showlegend=False,
            hovertext=[f"{z.direction.name} | L1={z.L1_price:.2f} "
                       f"L2={z.L2_price:.2f} | created {z.zone_created_time} | {tag}"],
            hoverinfo="text"))

    fig.update_layout(
        title=f"B2B zones on XAUUSD {tf.upper()} (IS, close-line) — last {last_n} bars",
        xaxis=dict(title="time (GMT+3 bar open)", range=[w0, w1]),
        yaxis=dict(title="close (bid)", range=[ylo, yhi]),   # locked to close range
        template="plotly_white", height=780, hovermode="x unified")

    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_fp = os.path.join(out_dir, f"zones_{tf}_is_last{last_n}.html")
    fig.write_html(out_fp)
    print(f"[render] wrote {out_fp}")


if __name__ == "__main__":
    main()
