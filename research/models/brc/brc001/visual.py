"""
visual.py — BRC-001 5-pointer zone visualizer (matplotlib).

Gate-2 eyeball tool: SEE that the Path-B detector (zones.py) places the five
structural points on real swings and builds a sane zone box. Close-price LINE
(not candlesticks) for an uncluttered view — detection is close-based throughout
(struct close-pivots + P4 close-confirmation), so the close line is the faithful
series and removes wick noise that obscured the geometry.

Two modes:
  zone <i>      per-zone ZOOM (default) — one zone in its P5->P4+lookahead window.
                The real geometry audit: P1-P5 labelled, L1/L2 + P5 barrier lines,
                zone rectangle, P4 close marked. Verify time-order + level placement.
  overview <n>  last-n-bars slice with every in-view zone as a faint rectangle —
                density/placement sanity. EXPECT heavy overlap: 1254 raw zones, no
                dedup yet (that overlap is the visual case for the deferred filters).

Reuses struct's --mpl/--png convention (task 75): native GUI window, or headless
PNG (agent-eyeballable) under research/outputs/brc001/.

Usage:
  python research/models/brc/brc001/visual.py zone 0 --png       # zone #0, headless PNG
  python research/models/brc/brc001/visual.py zone 12            # zone #12, GUI window
  python research/models/brc/brc001/visual.py overview 120 --png # last 120 D1 bars
"""
from __future__ import annotations

import sys
from pathlib import Path

import zones as Z
from zones import SignalDirection

REPO = Path(__file__).resolve().parents[4]
OUT_DIR = REPO / "research" / "outputs" / "brc001"

CLR_LINE = "#8a8a8a"
CLR_UP = "#26c281"     # bullish candle body
CLR_DN = "#e8467c"     # bearish candle body
CLR_SELL = "#e8467c"   # SELL zone (red)
CLR_BUY = "#26c281"    # BUY zone (green)
CLR_PT = "#ffd166"     # P-point dots
CLR_P4 = "#7ee787"     # P4 confirmation close
CLR_BAR = "#9aa0ff"    # P5 barrier line


def _setup(ax, fig):
    fig.patch.set_facecolor("#111111"); ax.set_facecolor("#111111")
    ax.tick_params(colors="#aaaaaa")
    [s.set_color("#444444") for s in ax.spines.values()]


def _line(ax, dfv):
    """Close-price LINE on an integer x-axis (0..len-1) — no weekend gaps, clean
    zoom. Detection is close-based (struct close-pivots + P4 close-confirm), so a
    close line is the faithful, uncluttered view. Caller maps times->positions
    via _pos(). Small dots mark each bar's close so swings are still locatable."""
    c = dfv["close"].values
    x = range(len(dfv))
    ax.plot(x, c, color=CLR_LINE, lw=1.2, zorder=2)
    ax.scatter(x, c, s=8, color=CLR_LINE, zorder=2)


def _date_ticks(ax, dfv, n=8):
    import numpy as np
    idx = np.linspace(0, len(dfv) - 1, min(n, len(dfv))).astype(int)
    ax.set_xticks(idx)
    ax.set_xticklabels([str(dfv["time"].iloc[i])[:10] for i in idx], rotation=0, fontsize=8)


def _load():
    df = Z.sp.load("D1")
    zones = Z.detect_zones("D1")
    pos = {Z.pd.Timestamp(t): i for i, t in enumerate(df["time"])}
    return df, zones, pos


def _pos(pos: dict, t) -> int:
    return pos.get(Z.pd.Timestamp(t), -1)


def plot_zone(i: int, lookahead: int = 14, pad_left: int = 3,
              do_open: bool = True, save_png: bool = False) -> Path:
    import matplotlib
    if save_png:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    df, zones, pos = _load()
    if not (0 <= i < len(zones)):
        raise SystemExit(f"zone index {i} out of range (have {len(zones)} zones)")
    z = zones[i]
    sell = z.direction == SignalDirection.BEARISH
    zclr = CLR_SELL if sell else CLR_BUY

    p5i, p4i = _pos(pos, z.p5_time), _pos(pos, z.p4_time)
    lo = max(0, p5i - pad_left); hi = min(len(df), p4i + lookahead + 1)
    dfv = df.iloc[lo:hi].reset_index(drop=True)

    def X(t):  # map a P-time to window-local x
        return _pos(pos, t) - lo

    fig, ax = plt.subplots(figsize=(13, 7.4)); _setup(ax, fig)
    _line(ax, dfv)

    # zone rectangle: P1 .. P4, spanning L1<->L2
    x1, x4 = X(z.p1_time), X(z.p4_time)
    ylo, yhi = min(z.l1_price, z.l2_price), max(z.l1_price, z.l2_price)
    ax.add_patch(Rectangle((x1, ylo), max(x4 - x1, 0.5), yhi - ylo,
                           facecolor=zclr, alpha=0.13, edgecolor=zclr, lw=1.0, zorder=1))
    # L1 (entry), L2 (stop), P5 barrier — dotted horizontals
    ax.axhline(z.l1_price, ls="--", lw=1.0, color=zclr, alpha=0.8)
    ax.axhline(z.l2_price, ls="--", lw=1.0, color=zclr, alpha=0.5)
    ax.axhline(z.p5_price, ls=":", lw=1.1, color=CLR_BAR, alpha=0.9)
    ax.text(0.2, z.l1_price, "L1", color=zclr, fontsize=8, va="bottom")
    ax.text(0.2, z.l2_price, "L2", color=zclr, fontsize=8, va="bottom")
    ax.text(0.2, z.p5_price, "P5 barrier", color=CLR_BAR, fontsize=8, va="bottom")

    # the five structural points, labelled
    pts = [("P1", z.p1_time, z.p1_price), ("P2", z.p2_time, z.l1_price),
           ("P3", z.p3_time, z.p3_price), ("P5", z.p5_time, z.p5_price)]
    for name, t, price in pts:
        ax.scatter(X(t), price, s=70, c=CLR_PT, zorder=5, edgecolors="#111111")
        ax.annotate(name, (X(t), price), color=CLR_PT, fontsize=9,
                    xytext=(0, 8), textcoords="offset points", ha="center")
    ax.scatter(X(z.p4_time), z.p4_price, s=85, marker="D", c=CLR_P4, zorder=5, edgecolors="#111111")
    ax.annotate("P4", (X(z.p4_time), z.p4_price), color=CLR_P4, fontsize=9,
                xytext=(0, -14), textcoords="offset points", ha="center")

    d = "SELL" if sell else "BUY"
    ok = (z.p4_price < z.p5_price) if sell else (z.p4_price > z.p5_price)
    ax.set_title(f"BRC-001 zone #{i}  {d}  ·  L1={z.l1_price:.2f} L2={z.l2_price:.2f} "
                 f"P5={z.p5_price:.2f}  ·  P4 close={z.p4_price:.2f} "
                 f"({'beyond P5 ✓' if ok else 'NOT beyond P5 ✗'})", color="#dddddd", fontsize=11)
    _date_ticks(ax, dfv)
    fig.tight_layout()

    print(f"zone #{i} {d}  P5={str(z.p5_time)[:10]} P1={str(z.p1_time)[:10]} "
          f"P2={str(z.p2_time)[:10]} P3={str(z.p3_time)[:10]} P4={str(z.p4_time)[:10]}  "
          f"L1={z.l1_price:.2f} L2={z.l2_price:.2f} P4close={z.p4_price:.2f} "
          f"beyond_P5={ok}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"zone_{i}.png"
    if save_png:
        fig.savefig(str(out), dpi=110, facecolor=fig.get_facecolor()); print(f"wrote {out}")
    elif do_open:
        plt.show()
    return out


def plot_overview(n_bars: int = 120, do_open: bool = True, save_png: bool = False) -> Path:
    import matplotlib
    if save_png:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    df, zones, pos = _load()
    lo = max(0, len(df) - n_bars)
    dfv = df.iloc[lo:].reset_index(drop=True)
    tmin = df["time"].iloc[lo]

    fig, ax = plt.subplots(figsize=(15, 7.6)); _setup(ax, fig)
    _line(ax, dfv)

    in_view = [z for z in zones if Z.pd.Timestamp(z.p4_time) >= Z.pd.Timestamp(tmin)]
    for z in in_view:
        sell = z.direction == SignalDirection.BEARISH
        zclr = CLR_SELL if sell else CLR_BUY
        x1, x4 = _pos(pos, z.p1_time) - lo, _pos(pos, z.p4_time) - lo
        if x1 < 0:
            x1 = 0
        ylo, yhi = min(z.l1_price, z.l2_price), max(z.l1_price, z.l2_price)
        ax.add_patch(Rectangle((x1, ylo), max(x4 - x1, 0.5), yhi - ylo,
                               facecolor=zclr, alpha=0.09, edgecolor=zclr, lw=0.6, zorder=1))

    ax.set_title(f"BRC-001 — D1 minimal-core zones · last {len(dfv)} bars · "
                 f"{len(in_view)} zones in view (raw, no dedup)", color="#dddddd", fontsize=11)
    _date_ticks(ax, dfv, n=10)
    fig.tight_layout()
    print(f"bars={len(dfv)}  zones_in_view={len(in_view)} "
          f"(sell={sum(1 for z in in_view if z.direction==SignalDirection.BEARISH)})")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "overview.png"
    if save_png:
        fig.savefig(str(out), dpi=110, facecolor=fig.get_facecolor()); print(f"wrote {out}")
    elif do_open:
        plt.show()
    return out


def _main(argv: list[str]) -> None:
    flags = [a for a in argv if a.startswith("--")]
    pos = [a for a in argv if not a.startswith("--")]
    kind = pos[0] if pos and not pos[0].isdigit() else "zone"
    nums = [int(a) for a in pos if a.lstrip("-").isdigit()]
    save_png = "--png" in flags
    do_open = "--no-open" not in flags

    if kind == "zone":
        plot_zone(nums[0] if nums else 0, do_open=do_open, save_png=save_png)
    elif kind == "overview":
        plot_overview(nums[0] if nums else 120, do_open=do_open, save_png=save_png)
    else:
        raise SystemExit(f"unknown viz '{kind}' (have: zone, overview)")


if __name__ == "__main__":
    _main(sys.argv[1:])
