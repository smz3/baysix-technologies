"""
viz_swings.py — STRUCT-001 Tier-1 swing-point visualizer (Plotly).

Draws D1 candlesticks (Arctic) + Python-detected swings marked at the pivot
bar's CLOSE — the exact placement MT5 uses (Visualizer.mqh DrawSwingPoint puts
the bullet at price == close_price). Detection is the SHARED engine
b2b/sigma_core/b2b/detectors/swing_points.py, parity-proven at InpSwingWindow=3
(see audit_detector_causality.py). So these dots land where the EA draws them.

MT5 colors both swings clrMistyRose; here HIGH/LOW are colored distinctly for
readability (placement, not hue, is the fidelity point).

Usage:
  python research/models/struct/struct001/viz_swings.py            # last 300 D1 bars
  python research/models/struct/struct001/viz_swings.py 600        # last 600 bars
  python research/models/struct/struct001/viz_swings.py 600 --no-open
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "b2b"))
sys.path.insert(0, str(REPO / "research" / "code"))

import pandas as pd                                                   # noqa: E402
import plotly.graph_objects as go                                    # noqa: E402
import arctic_io as aio                                              # noqa: E402
from sigma_core.b2b.detectors.swing_points import detect_swings      # noqa: E402

OUT_DIR = REPO / "research" / "outputs" / "struct001"
CLR_HIGH = "#e8467c"   # swing-high marker (MT5: clrMistyRose, recolored for clarity)
CLR_LOW = "#2f9e8f"    # swing-low marker


def build(n_bars: int = 300, do_open: bool = True) -> Path:
    d = aio.daily_bars().reset_index()
    d.columns = [c.lower() for c in d.columns]
    df = d.rename(columns={"date": "time"})[["time", "open", "high", "low", "close"]]

    swings = detect_swings(df)                      # full-history detection (no edge effects)
    df = df.tail(n_bars).reset_index(drop=True)     # then window the view
    tmin = df["time"].iloc[0]
    sw = [s for s in swings if s.time >= tmin]
    highs = [s for s in sw if s.type.name == "HIGH"]
    lows = [s for s in sw if s.type.name == "LOW"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["close"], mode="lines", name="XAUUSD D1 close",
        line=dict(color="#8a8a8a", width=1.2),
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
        title=f"STRUCT-001 — XAUUSD D1 close-based swings (InpSwingWindow=3) · last {len(df)} bars",
        template="plotly_dark", xaxis_rangeslider_visible=False,
        height=760, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=0),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "swings_d1.html"
    fig.write_html(str(out))
    print(f"bars={len(df)}  swings_in_view={len(sw)}  (H={len(highs)} L={len(lows)})")
    print(f"wrote {out}")
    if do_open:
        webbrowser.open(out.as_uri())
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 300
    build(n_bars=n, do_open="--no-open" not in sys.argv)
