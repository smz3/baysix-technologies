"""
visual.py — STRUCT-001 universal visualizer (Plotly).

ONE viz module for every struct artifact. Add render functions here as the idea
grows (plot_swings now; breakouts / zones / HH-HL structure next) instead of
scattering Plotly into each detector. Detection stays pure in swingpoints.py.

Swings are marked at the pivot bar's CLOSE — the exact placement MT5 uses
(Visualizer.mqh DrawSwingPoint: bullet at price == close_price). On a close line
the dots sit ON the line, which is the visual tell of MQH parity. MT5 colors both
swings clrMistyRose; HIGH/LOW are recolored here for readability.

Usage:
  python research/models/struct/struct001/visual.py                      # swings, last 300 D1
  python research/models/struct/struct001/visual.py swings 600           # last 600 bars
  python research/models/struct/struct001/visual.py swings 600 --window 5 # wider pivot
  python research/models/struct/struct001/visual.py swings 600 --no-open
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import plotly.graph_objects as go

import swingpoints as sp
import rawbreakout as rb
from sigma_core.b2b.models.structures import SignalDirection

REPO = Path(__file__).resolve().parents[4]
OUT_DIR = REPO / "research" / "outputs" / "struct001"
CLR_HIGH = "#e8467c"   # swing-high marker (MT5: clrMistyRose, recolored for clarity)
CLR_LOW = "#2f9e8f"    # swing-low marker
CLR_LINE = "#8a8a8a"
CLR_BULL = "#26c281"   # bullish breakout
CLR_BEAR = "#e8467c"   # bearish breakout
CLR_LVL = "rgba(150,150,150,0.35)"   # broken-swing level segment


def _open(out: Path, do_open: bool) -> None:
    print(f"wrote {out}")
    if do_open:
        webbrowser.open(out.as_uri())


def plot_swings(n_bars: int = 300, swing_window: int = 3, do_open: bool = True) -> Path:
    """D1 close-line + swings (detected on full history, then windowed to last n_bars)."""
    df, swings = sp.swings_d1(swing_window=swing_window)
    df = df.tail(n_bars).reset_index(drop=True)
    tmin = df["time"].iloc[0]
    sw = [s for s in swings if s.time >= tmin]
    highs = [s for s in sw if s.type.name == "HIGH"]
    lows = [s for s in sw if s.type.name == "LOW"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["close"], mode="lines", name="XAUUSD D1 close",
        line=dict(color=CLR_LINE, width=1.2),
        hovertemplate="%{x|%Y-%m-%d}<br>close %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[s.time for s in highs], y=[s.price for s in highs], mode="markers",
        name=f"Swing High ({len(highs)})", marker=dict(symbol="circle", size=9, color=CLR_HIGH),
        hovertemplate="SWING HIGH<br>%{x|%Y-%m-%d}<br>close %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[s.time for s in lows], y=[s.price for s in lows], mode="markers",
        name=f"Swing Low ({len(lows)})", marker=dict(symbol="circle", size=9, color=CLR_LOW),
        hovertemplate="SWING LOW<br>%{x|%Y-%m-%d}<br>close %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"STRUCT-001 — XAUUSD D1 close-based swings (window={swing_window}) · last {len(df)} bars",
        template="plotly_dark", xaxis_rangeslider_visible=False,
        height=760, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=0),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "swings_d1.html"
    fig.write_html(str(out))
    print(f"bars={len(df)}  window={swing_window}  swings_in_view={len(sw)}  (H={len(highs)} L={len(lows)})")
    _open(out, do_open)
    return out


def plot_breakouts(n_bars: int = 300, swing_window: int = 3, do_open: bool = True) -> Path:
    """D1 close-line + breakouts: arrows at the breakout bar's close + the broken-swing
    level segment (swing time → breakout time at the broken price). Detected on full
    history, then windowed to last n_bars."""
    df, _swings, bk = rb.raw_breakouts_d1(swing_window=swing_window)
    df = df.tail(n_bars).reset_index(drop=True)
    tmin = df["time"].iloc[0]
    bk = [b for b in bk if b.breakout_bar_time >= tmin]
    bull = [b for b in bk if b.direction == SignalDirection.BULLISH]
    bear = [b for b in bk if b.direction == SignalDirection.BEARISH]

    # broken-swing level segments (None-separated for one trace)
    lx, ly = [], []
    for b in bk:
        lx += [b.broken_swing_time, b.breakout_bar_time, None]
        ly += [b.broken_swing_price, b.broken_swing_price, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["close"], mode="lines", name="XAUUSD D1 close",
        line=dict(color=CLR_LINE, width=1.2),
        hovertemplate="%{x|%Y-%m-%d}<br>close %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=lx, y=ly, mode="lines", name="broken swing level",
        line=dict(color=CLR_LVL, width=1, dash="dot"), hoverinfo="skip", showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=[b.breakout_bar_time for b in bull], y=[b.breakout_bar_close_price for b in bull],
        mode="markers", name=f"Bullish break ({len(bull)})",
        marker=dict(symbol="triangle-up", size=10, color=CLR_BULL),
        customdata=[(b.broken_swing_price, b.impulse_start_price) for b in bull],
        hovertemplate="BULLISH break<br>%{x|%Y-%m-%d}<br>close %{y:.2f}"
                      "<br>broke high %{customdata[0]:.2f}<br>L2 %{customdata[1]:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[b.breakout_bar_time for b in bear], y=[b.breakout_bar_close_price for b in bear],
        mode="markers", name=f"Bearish break ({len(bear)})",
        marker=dict(symbol="triangle-down", size=10, color=CLR_BEAR),
        customdata=[(b.broken_swing_price, b.impulse_start_price) for b in bear],
        hovertemplate="BEARISH break<br>%{x|%Y-%m-%d}<br>close %{y:.2f}"
                      "<br>broke low %{customdata[0]:.2f}<br>L2 %{customdata[1]:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"STRUCT-001 — XAUUSD D1 raw breakouts (window={swing_window}) · last {len(df)} bars",
        template="plotly_dark", xaxis_rangeslider_visible=False,
        height=760, hovermode="closest", legend=dict(orientation="h", y=1.02, x=0),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "breakouts_d1.html"
    fig.write_html(str(out))
    print(f"bars={len(df)}  window={swing_window}  breakouts_in_view={len(bk)} (bull={len(bull)} bear={len(bear)})")
    _open(out, do_open)
    return out


def _main(argv: list[str]) -> None:
    flags = [a for a in argv if a.startswith("--")]
    pos = [a for a in argv if not a.startswith("--")]
    kind = pos[0] if pos and not pos[0].isdigit() else "swings"
    nums = [int(a) for a in pos if a.isdigit()]
    n_bars = nums[0] if nums else 300
    window = 3
    if "--window" in argv:
        window = int(argv[argv.index("--window") + 1])
    do_open = "--no-open" not in flags

    if kind == "swings":
        plot_swings(n_bars=n_bars, swing_window=window, do_open=do_open)
    elif kind == "breakouts":
        plot_breakouts(n_bars=n_bars, swing_window=window, do_open=do_open)
    else:
        raise SystemExit(f"unknown viz '{kind}' (have: swings, breakouts)")


if __name__ == "__main__":
    _main(sys.argv[1:])
