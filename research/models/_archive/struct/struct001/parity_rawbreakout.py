"""
parity_rawbreakout.py — task 77 oracle+parity gate for the vectorized breakout port.

Asserts the numba `detect_raw_breakouts` is BYTE-IDENTICAL to the frozen pure-Python
oracle `_detect_raw_breakouts_py` across swing windows {3,5,7} on {D1,H1,M15}, then
benchmarks both. Every field of every RawBreakoutInfo must match; any mismatch is a
hard failure (the swap does not ship unless this prints ALL GREEN).

  python research/models/struct/struct001/parity_rawbreakout.py
"""
from __future__ import annotations

import time as _time

from tqdm import tqdm

import swingpoints as sp
import rawbreakout as rb
from structures import DetectionConfig

TFS = ["D1", "H1", "M15"]
WINDOWS = [3, 5, 7]

_FIELDS = [
    "breakout_bar_time", "breakout_bar_close_price", "direction", "timeframe",
    "broken_swing_price", "broken_swing_time", "broken_swing_close_price",
    "broken_swing_type", "impulse_start_price", "breakout_bar_index",
    "broken_swing_bar_index",
]


def _diff(a, b) -> list[str]:
    """Field-by-field diff of two RawBreakoutInfo lists. Empty list = identical."""
    msgs: list[str] = []
    if len(a) != len(b):
        msgs.append(f"  COUNT mismatch: oracle={len(a)} numba={len(b)}")
        return msgs
    for i, (x, y) in enumerate(zip(a, b)):
        for f in _FIELDS:
            xv, yv = getattr(x, f), getattr(y, f)
            if xv != yv:
                msgs.append(f"  bo[{i}].{f}: oracle={xv!r} numba={yv!r}")
    return msgs


def main() -> None:
    all_green = True
    bench: list[tuple[str, int, int, float, float]] = []

    for tf in TFS:
        for w in WINDOWS:
            df, swings = sp.swings(tf, swing_window=w)
            cfg = DetectionConfig(swing_window=w)

            t0 = _time.perf_counter()
            oracle = rb._detect_raw_breakouts_py(df, swings, cfg)
            t_py = _time.perf_counter() - t0

            t0 = _time.perf_counter()
            fast = rb.detect_raw_breakouts(df, swings, cfg)   # incl. JIT on first call
            t_nb = _time.perf_counter() - t0

            msgs = _diff(oracle, fast)
            status = "GREEN" if not msgs else "RED"
            if msgs:
                all_green = False
            print(f"[{tf:>3} w={w}] bars={len(df):>6} swings={len(swings):>5} "
                  f"breakouts={len(oracle):>5}  py={t_py:7.3f}s  nb={t_nb:7.3f}s  "
                  f"{status}")
            for m in msgs[:10]:
                print(m)
            bench.append((tf, w, len(oracle), t_py, t_nb))

    print("\n── speedup (py / nb, nb second-call warm) ──")
    for tf, w, nbo, t_py, t_nb in bench:
        spd = t_py / t_nb if t_nb > 0 else float("inf")
        print(f"  {tf:>3} w={w}: {spd:6.1f}x  ({t_py:.3f}s → {t_nb:.3f}s)")

    print(f"\n{'[PASS] ALL GREEN -- byte-identical, safe to ship' if all_green else '[FAIL] PARITY FAILED -- DO NOT SHIP'}")
    raise SystemExit(0 if all_green else 1)


if __name__ == "__main__":
    main()
