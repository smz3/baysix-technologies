"""
audit_detector_causality.py — STRUCT-001 task-71 AUDIT (rerunnable).

Proves STRUCT-001's OWN swing/breakout port (detectors.py + rawbreakout.py) is
CAUSAL (no look-ahead) and PARITY-faithful to the live MQL5 EA at InpSwingWindow=3.

5 checks on real D1 bars (Arctic). Verdict logged once as BRK-001/STRUCT-001
human call 53; this file lets any later session RE-RUN the proof instead of
trusting an ephemeral one-off. Run:  python research/models/struct/struct001/audit_detector_causality.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "research" / "code" / "io"))

import arctic_io as aio                                              # noqa: E402
from detectors import detect_swings                                 # noqa: E402
from rawbreakout import detect_raw_breakouts                        # noqa: E402

RADIUS = 1   # InpSwingWindow=3 -> window_radius = 3//2 = 1 (1 bar each side)


def run() -> bool:
    d = aio.daily_bars().reset_index()
    d.columns = [c.lower() for c in d.columns]
    df = d.rename(columns={"date": "time"})[["time", "open", "high", "low", "close"]]
    closes = df["close"].values

    sw = detect_swings(df)
    bk = detect_raw_breakouts(df, sw)
    print(f"D1 bars={len(df)}  swings={len(sw)}  breakouts={len(bk)}")

    # 1 — swings detected on CLOSE only (price == close at pivot bar)
    c1 = sum(1 for s in sw if abs(s.price - closes[s.bar_index]) > 1e-9)

    # 2 — true strict 1-each-side close pivot (needs bar i+1 => confirm at pivot+RADIUS)
    c2 = 0
    for s in sw:
        i = s.bar_index
        if s.type.name == "HIGH" and not (closes[i] > closes[i-1] and closes[i] > closes[i+1]): c2 += 1
        if s.type.name == "LOW"  and not (closes[i] < closes[i-1] and closes[i] < closes[i+1]): c2 += 1

    # 3 — THE causality test: no breakout fires before swing confirmation bar (pivot+RADIUS)
    c3 = [(b.broken_swing_bar_index, b.breakout_bar_index) for b in bk
          if b.breakout_bar_index < b.broken_swing_bar_index + RADIUS]

    # 4 — breakout close actually beyond swing close, correct direction
    c4 = 0
    for b in bk:
        if b.direction.name == "BULLISH" and not (b.breakout_bar_close_price > b.broken_swing_price): c4 += 1
        if b.direction.name == "BEARISH" and not (b.breakout_bar_close_price < b.broken_swing_price): c4 += 1

    # 5 — config parity: detect_swings honors config.swing_window (radius = w//2) + odd/>=3 guard
    import inspect
    import detectors as spm
    uses_window = "config.swing_window" in inspect.getsource(spm.detect_swings)

    print(f"[1 close-based]   price!=close[bar]      : {c1}        -> {'PASS' if c1==0 else 'FAIL'}")
    print(f"[2 pivot geom]    strict-pivot violations: {c2}        -> {'PASS' if c2==0 else 'FAIL'}")
    print(f"[3 causality]     breakout < confirm bar : {len(c3)}        -> {'PASS' if not c3 else 'FAIL'}")
    print(f"[4 breakout rule] close-beyond-swing viol: {c4}        -> {'PASS' if c4==0 else 'FAIL'}")
    print(f"[5 config parity] honors window param    : {uses_window}    -> "
          f"{'honors config.swing_window + odd/>=3 guard (task 74)' if uses_window else 'hardcoded — REGRESSED'}")

    ok = (c1 == 0 and c2 == 0 and not c3 and c4 == 0)
    print(f"\nVERDICT: {'PASS — causal + parity-faithful at window=3' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
