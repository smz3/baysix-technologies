"""
payoff_asymmetry.py — BRC-001 the ONE surviving discovery test (handover 2026-06-17
Afternoon2, Next #1).

The symmetric +-1R retest race was FALSIFIED vs trend beta (strategy_log #51): BRC's
win rate matched a random same-dir entry. The only thread left is PAYOFF asymmetry —
winners' MFE ran ~2R while the stop is 1R. So the question is no longer "does the
zone predict direction" but "does an UNMANAGED let-winners-run hold from the L1
retest (stop=L2, no cap) beat the SAME let-run rule fired from a random same-direction
bar, holding R and the entry count fixed?".

Control = trend beta. Gold ran 3.6x over 2016->2026, so any always-in-the-trend rule
makes money in the down/up-tilted direction regardless of the zone. The matched
baseline strips that out:
    - same number of entries as BRC zones in the sample,
    - same per-zone R (paired — the R distribution is identical),
    - same direction (paired),
    - same exit rule (let_run: stop at -1R close, else hold to data end),
    - entry bar drawn UNIFORMLY at random from the series.
Bootstrap the baseline mean realized R; z-score BRC's mean against it. If BRC ~ beta
again => 2nd FALSIFIED hypothesis => BRC killable (rule 8b needs >=2).

Cost-free, descriptive, pre-Gate-3 (Gate 3 stays CLOSED until a rule is frozen AND
beats beta). D1 single-TF atom.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
if str(here) not in _sys.path:
    _sys.path.insert(0, str(here))

from zones import BrcZone        # noqa: E402  (import first: runs _struct_on_path)
from structures import SignalDirection  # noqa: E402
import rawbreakout as rb         # noqa: E402
import zones as zmod             # noqa: E402
import lifecycle as lc           # noqa: E402
import retest as rt              # noqa: E402
import continuation as cont      # noqa: E402


def _baseline_realized_r(closes: np.ndarray, k: int, sell: bool, R: float) -> float:
    """let_run from a random entry bar k: entry=close[k], stop=entry +- R against the
    trade, no cap, exit at the first close beyond the stop else the last close."""
    entry = closes[k]
    stop = entry + R if sell else entry - R
    n = len(closes)
    for j in range(k, n):
        c = closes[j]
        dead = (c > stop) if sell else (c < stop)
        if dead:
            return (entry - c) / R if sell else (c - entry) / R
    c = closes[n - 1]
    return (entry - c) / R if sell else (c - entry) / R


def run(tf: str = "D1", swing_window: int = 3, n_boot: int = 2000, seed: int = 7) -> None:
    df, _, _ = rb.raw_breakouts(tf, swing_window=swing_window)
    zs = zmod.detect_zones(tf, swing_window=swing_window)
    lives = {id(L.zone): L for L in lc.label_lifecycles(df, zs)}
    closes = df["close"].values.astype(float)
    n = len(closes)

    # --- BRC sample: zones whose pullback re-touched L1 (entry = the L1 retest) ---
    real_r, real_dir, real_R = [], [], []
    for z in zs:
        life = lives[id(z)]
        lad = rt.find_retest_ladder(df, z, life)
        t = lad.touches.get(1)            # T1 = L1 retest = the entry trigger
        if t is None:
            continue
        lr = cont.let_run(df, z, t, life)
        real_r.append(lr.realized_r)
        real_dir.append(z.direction == SignalDirection.BEARISH)   # True = SELL
        real_R.append(abs(z.l1_price - z.l2_price))
    real_r = np.array(real_r)
    real_dir = np.array(real_dir)
    real_R = np.array(real_R)
    m = len(real_r)

    brc_mean = real_r.mean()
    brc_win = (real_r > 0).mean()
    brc_med = float(np.median(real_r))

    # per-direction BRC means (the trend-beta split the finding flagged)
    sell_mask = real_dir
    brc_sell = real_r[sell_mask].mean() if sell_mask.any() else float("nan")
    brc_buy = real_r[~sell_mask].mean() if (~sell_mask).any() else float("nan")

    # --- matched random same-dir baseline (paired R + direction, uniform entry) ---
    rng = np.random.default_rng(seed)
    boot_mean = np.empty(n_boot)
    boot_win = np.empty(n_boot)
    for b in range(n_boot):
        ks = rng.integers(0, n - 1, size=m)         # random entry bar per matched trade
        rs = np.fromiter(
            (_baseline_realized_r(closes, int(ks[i]), bool(real_dir[i]), float(real_R[i]))
             for i in range(m)),
            dtype=float, count=m,
        )
        boot_mean[b] = rs.mean()
        boot_win[b] = (rs > 0).mean()

    bmu, bsd = boot_mean.mean(), boot_mean.std(ddof=1)
    z_mean = (brc_mean - bmu) / bsd if bsd > 0 else float("nan")
    pct_mean = (boot_mean < brc_mean).mean()
    wmu, wsd = boot_win.mean(), boot_win.std(ddof=1)
    z_win = (brc_win - wmu) / wsd if wsd > 0 else float("nan")

    print(f"=== BRC-001 payoff-asymmetry test (let-run-to-invalidation) {tf} "
          f"window={swing_window} ===")
    print(f"sample: {m} zones with an L1 retest "
          f"(SELL {int(sell_mask.sum())} / BUY {int((~sell_mask).sum())})")
    print(f"  invalidated/runner split: "
          f"{int((real_r < 0).sum())} losers / {int((real_r > 0).sum())} winners")
    print()
    print(f"BRC   E[R] = {brc_mean:+.4f}   win% = {100*brc_win:5.1f}   "
          f"median = {brc_med:+.3f}R")
    print(f"        by dir:  SELL {brc_sell:+.4f}R   BUY {brc_buy:+.4f}R")
    print(f"BETA  E[R] = {bmu:+.4f} +- {bsd:.4f}   win% = {100*wmu:5.1f} +- {100*wsd:.1f}"
          f"   (matched random same-dir, n_boot={n_boot})")
    print()
    print(f"  E[R]  vs beta:  z = {z_mean:+.2f}   percentile = {100*pct_mean:5.1f}%")
    print(f"  win%  vs beta:  z = {z_win:+.2f}")
    print()
    verdict = ("BEATS beta (z>=+2)" if z_mean >= 2 else
               "INCONCLUSIVE (+1..+2)" if z_mean >= 1 else
               "~= beta => FALSIFIED (no payoff edge over trend)")
    print(f"  VERDICT: {verdict}")


def _main(argv: list[str]) -> None:
    tf = argv[argv.index("--tf") + 1].upper() if "--tf" in argv else "D1"
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else 3
    nb = int(argv[argv.index("--nboot") + 1]) if "--nboot" in argv else 2000
    run(tf, swing_window=window, n_boot=nb)


if __name__ == "__main__":
    _main(_sys.argv[1:])
