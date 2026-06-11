"""
Gate-7 root-cause TEST (systematic-debugging Phase 3): does the EA's entry rule
explain the direction flips?

For each OOS session, compute the breakout DIRECTION two ways on the SAME ticks:
  PY rule  — mid price, half-spread inset  (Python research, _simulate_day)
  EA rule  — bid price vs bid-based OR, no inset  (baysix_orb_001.mq5 ComputeOpeningRange+TryEnter)
then compare both against the ACTUAL tester directions (tester_trades_parsed.csv).

Hypothesis: EA-rule direction ≈ tester (≈100%), PY-rule vs tester ≈ the 51.5% we saw.
If confirmed -> the flip root cause is the entry price basis (bid+bar+no-inset vs mid+inset).

    python -X utf8 research/models/orb/orb001/fidelity_emulate.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from research.models.orb.orb001.trail_oos import (
    OR_MIN, SPREAD, IS_END_TS, OOS_MONTHS, NS_H, NS_M, NS_D)
from research.models.orb.orb001.orb_core import LONDON_ANCHOR_HOUR
from research.code.session_cache import session_files

OUT = REPO / "research" / "outputs" / "orb" / "fidelity"


def _first(mask):
    return int(np.argmax(mask)) if mask.any() else None


def _dir(i_up, i_dn):
    if i_up is None and i_dn is None:
        return None
    return "long" if (i_dn is None or (i_up is not None and i_up <= i_dn)) else "short"


def _day_dirs(ts, bid, ask, day0):
    """Return (py_dir, ea_dir) for one session, or None."""
    half = SPREAD * 0.5
    mid = (bid + ask) * 0.5
    anchor = day0 + LONDON_ANCHOR_HOUR * NS_H
    or_end = anchor + OR_MIN * NS_M
    eod = day0 + 21 * NS_H

    in_or = (ts >= anchor) & (ts < or_end)
    if not in_or.any():
        return None
    or_hi_m, or_lo_m = mid[in_or].max(), mid[in_or].min()       # PY: mid OR
    or_hi_b, or_lo_b = bid[in_or].max(), bid[in_or].min()       # EA: bid (M1-bar) OR
    if or_hi_m <= or_lo_m:
        return None

    post = (ts >= or_end) & (ts < eod)
    if not post.any():
        return None
    pmid, pbid = mid[post], bid[post]

    # PY rule: mid with half-spread inset
    py = _dir(_first(pmid >= or_hi_m - half), _first(pmid <= or_lo_m + half))
    # EA rule: bid vs bid-OR, no inset (TryEnter: bid>=or_high -> long; bid<=or_low -> short)
    ea = _dir(_first(pbid >= or_hi_b), _first(pbid <= or_lo_b))
    return py, ea, or_hi_m, or_lo_m, or_hi_b, or_lo_b


def main():
    files = session_files(OOS_MONTHS)
    if not files:
        sys.exit("No session-cache files.")
    is_cut = np.datetime64(IS_END_TS)
    rows = []
    for f in tqdm(files, desc="OOS dirs"):
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        df = df[df["ts_utc"].values >= is_cut]
        if df.empty:
            continue
        ts = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        bid = df["bid"].values
        ask = df["ask"].values
        day_key = ts // NS_D
        for d in np.unique(day_key):
            mk = day_key == d
            res = _day_dirs(ts[mk], bid[mk], ask[mk], int(d) * NS_D)
            if res is None:
                continue
            py, ea, or_hi_m, or_lo_m, or_hi_b, or_lo_b = res
            rows.append({"session_date": pd.Timestamp(int(d) * NS_D).strftime("%Y-%m-%d"),
                         "py_dir": py, "ea_dir": ea,
                         "or_hi_m": or_hi_m, "or_lo_m": or_lo_m,
                         "or_hi_b": or_hi_b, "or_lo_b": or_lo_b})
    em = pd.DataFrame(rows)

    # Compare against the actual tester directions
    te = pd.read_csv(OUT / "tester_trades_parsed.csv")[["session_date", "direction"]] \
        .rename(columns={"direction": "te_dir"})
    m = em.merge(te, on="session_date", how="inner").dropna(subset=["py_dir", "ea_dir", "te_dir"])

    def agree(a, b):
        return (m[a] == m[b]).mean() * 100

    print("\n" + "=" * 70)
    print("ROOT-CAUSE TEST — direction agreement on matched sessions (n=%d)" % len(m))
    print("=" * 70)
    print(f"  EA-rule  vs tester : {agree('ea_dir','te_dir'):5.1f}%   <- hypothesis: ~100%")
    print(f"  PY-rule  vs tester : {agree('py_dir','te_dir'):5.1f}%   <- the bug (research vs bot)")
    print(f"  PY-rule  vs EA-rule: {agree('py_dir','ea_dir'):5.1f}%")
    print(f"\n  (EA-rule reproduces the bot's own direction this well — if ~100%, the")
    print(f"   entry price-basis IS the flip root cause; PY/EA divergence == the bug.)")
    em.to_csv(OUT / "emulate_dirs.csv", index=False)
    m.to_csv(OUT / "emulate_vs_tester.csv", index=False)
    print(f"\n  outputs -> {OUT}")


if __name__ == "__main__":
    main()
