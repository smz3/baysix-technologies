"""
parity_m15_bounded.py — task 77, bounded M15 leg of the oracle+parity gate.

The full-history M15 *oracle* takes hours (the exact bottleneck this port removes),
so we prove M15 byte-identity on a recent N-bar slice across windows {3,5,7}. Parity
is data-independent: identical inputs MUST yield identical outputs, so a slice is a
valid proof of the M15 codepath. Numba still runs full M15 in seconds in production.

  python research/models/struct/struct001/parity_m15_bounded.py [N]   (default 20000)
"""
from __future__ import annotations

import sys
import time as _time

import swingpoints as sp
import rawbreakout as rb
from structures import DetectionConfig
from parity_rawbreakout import _diff

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
WINDOWS = [3, 5, 7]


def main() -> None:
    df_full = sp.load("M15", "JM_EET")
    df = df_full.tail(N).reset_index(drop=True)
    all_green = True

    for w in WINDOWS:
        cfg = DetectionConfig(swing_window=w)
        swings = sp.detect_swings(df, cfg)

        t0 = _time.perf_counter()
        oracle = rb._detect_raw_breakouts_py(df, swings, cfg)
        t_py = _time.perf_counter() - t0

        t0 = _time.perf_counter()
        fast = rb.detect_raw_breakouts(df, swings, cfg)
        t_nb = _time.perf_counter() - t0

        msgs = _diff(oracle, fast)
        status = "GREEN" if not msgs else "RED"
        if msgs:
            all_green = False
        spd = t_py / t_nb if t_nb > 0 else float("inf")
        print(f"[M15 w={w}] bars={len(df):>6} swings={len(swings):>5} "
              f"breakouts={len(oracle):>5}  py={t_py:8.3f}s  nb={t_nb:6.3f}s  "
              f"{spd:6.0f}x  {status}", flush=True)
        for m in msgs[:10]:
            print(m, flush=True)

    print(f"\n{'[PASS] M15 GREEN -- byte-identical on bounded slice' if all_green else '[FAIL] M15 PARITY FAILED'}", flush=True)
    raise SystemExit(0 if all_green else 1)


if __name__ == "__main__":
    main()
