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
from structures import SignalDirection

REPO = Path(__file__).resolve().parents[4]
OUT_DIR = REPO / "research" / "outputs" / "struct001"
CLR_HIGH = "#e8467c"   # swing-high marker (MT5: clrMistyRose, recolored for clarity)
CLR_LOW = "#2f9e8f"    # swing-low marker
CLR_LINE = "#8a8a8a"
CLR_BULL = "#26c281"   # bullish breakout — broken-swing dot
CLR_BEAR = "#e8467c"   # bearish breakout — broken-swing dot
CLR_BULL_BAR = "#7ee787"  # bullish breakout — breakout-BAR close dot (lighter green)
CLR_BEAR_BAR = "#ff9d6c"  # bearish breakout — breakout-BAR close dot (orange-red)


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
    """D1 close-line + breakouts, MT5-faithful (Visualizer.mqh DrawRawBreakout):
    the dot+label is anchored ON THE BROKEN SWING (broken_swing_time/price), NOT the
    breakout bar. The breakout-bar close lives only in the label text — exactly like
    MQH: '  Bob <swing> (<close>)' bullish / '  Bos …' bearish. No connector line, no
    breakout-bar arrow. Detected on full history, then windowed to last n_bars."""
    df, _swings, bk = rb.raw_breakouts_d1(swing_window=swing_window)
    df = df.tail(n_bars).reset_index(drop=True)
    tmin = df["time"].iloc[0]
    # window on the broken-swing anchor (the dot's own x), mirroring where MT5 draws it
    bk = [b for b in bk if b.broken_swing_time >= tmin]
    bull = [b for b in bk if b.direction == SignalDirection.BULLISH]
    bear = [b for b in bk if b.direction == SignalDirection.BEARISH]

    def _labels(items: list, tag: str) -> list[str]:
        # MT5 label: "  Bob <swing> (<close>)"  — text right-anchored (grows leftward)
        return [f"{tag} {b.broken_swing_price:.2f} ({b.breakout_bar_close_price:.2f}) " for b in items]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["close"], mode="lines", name="XAUUSD D1 close",
        line=dict(color=CLR_LINE, width=1.2),
        hovertemplate="%{x|%Y-%m-%d}<br>close %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[b.broken_swing_time for b in bull], y=[b.broken_swing_price for b in bull],
        mode="markers+text", name=f"Bob — bullish break ({len(bull)})",
        marker=dict(symbol="circle", size=8, color=CLR_BULL),
        text=_labels(bull, "Bob"), textposition="middle left",
        textfont=dict(color=CLR_BULL, size=9),
        customdata=[(b.breakout_bar_time, b.breakout_bar_close_price) for b in bull],
        hovertemplate="Bob (broke swing HIGH)<br>swing %{x|%Y-%m-%d} @ %{y:.2f}"
                      "<br>broke on %{customdata[0]|%Y-%m-%d} close %{customdata[1]:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[b.broken_swing_time for b in bear], y=[b.broken_swing_price for b in bear],
        mode="markers+text", name=f"Bos — bearish break ({len(bear)})",
        marker=dict(symbol="circle", size=8, color=CLR_BEAR),
        text=_labels(bear, "Bos"), textposition="middle left",
        textfont=dict(color=CLR_BEAR, size=9),
        customdata=[(b.breakout_bar_time, b.breakout_bar_close_price) for b in bear],
        hovertemplate="Bos (broke swing LOW)<br>swing %{x|%Y-%m-%d} @ %{y:.2f}"
                      "<br>broke on %{customdata[0]|%Y-%m-%d} close %{customdata[1]:.2f}<extra></extra>",
    ))
    # breakout-BAR close dots — the bar whose close confirmed the break (lighter shade),
    # labelled with that close price so it pairs visually with the broken-swing dot
    fig.add_trace(go.Scatter(
        x=[b.breakout_bar_time for b in bull], y=[b.breakout_bar_close_price for b in bull],
        mode="markers+text", name=f"Bob close ({len(bull)})",
        marker=dict(symbol="circle", size=7, color=CLR_BULL_BAR),
        text=[f" {b.breakout_bar_close_price:.2f}" for b in bull], textposition="middle right",
        textfont=dict(color=CLR_BULL_BAR, size=9),
        customdata=[(b.broken_swing_price,) for b in bull],
        hovertemplate="Bob breakout bar<br>%{x|%Y-%m-%d}<br>close %{y:.2f}"
                      "<br>broke high %{customdata[0]:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[b.breakout_bar_time for b in bear], y=[b.breakout_bar_close_price for b in bear],
        mode="markers+text", name=f"Bos close ({len(bear)})",
        marker=dict(symbol="circle", size=7, color=CLR_BEAR_BAR),
        text=[f" {b.breakout_bar_close_price:.2f}" for b in bear], textposition="middle right",
        textfont=dict(color=CLR_BEAR_BAR, size=9),
        customdata=[(b.broken_swing_price,) for b in bear],
        hovertemplate="Bos breakout bar<br>%{x|%Y-%m-%d}<br>close %{y:.2f}"
                      "<br>broke low %{customdata[0]:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"STRUCT-001 — XAUUSD D1 raw breakouts · MT5-faithful (window={swing_window}) · last {len(df)} bars",
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
