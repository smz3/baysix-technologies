"""
features.py — MSM-001 SHARED feature cache (full ladder), built ONCE from ticks.

The Gate-2 interaction test ([gate2_interaction.py]) collapsed the 9-rung ladder
into B + I and cached only those. The reframe hypotheses (C magnitude, A failed-
breakout, B slope, D vol-regime, E lead-lag — tasks 66-70) each need the INDIVIDUAL
rung returns + their causal z. So build the full ladder once and cache it; every
hypothesis reads the pkl, no hypothesis re-reads ticks.

Output cache: research/outputs/msm_features_full.pkl  (gitignored)
Columns (H4 decision grid, IS-sealed, leak-free):
  r0..r8   per-rung close-to-close returns  (L_k = 2^k M5 bars, ~M5 .. ~D1)
  z0..z8   CAUSAL expanding-z of each rung   (mean/std up to t-1, .shift(1))
  fwd      forward H4 return = LABEL (t -> t+48 M5)  — only ever a y, never an x
  price    M5 mid-close at decision t        (for spread-drag = $/price)

LOOK-AHEAD GUARDS (identical to gate2_interaction — see [[orb_unsorted_tick_lookahead]]):
  G1 sorted M5 from Arctic ticks, index asserted monotonic.
  G2 every rung return uses only past shifts (ends <= t).
  G3 causal standardisation: expanding mean/std up to t-1.
  G4 fwd H4 label on the non-overlapping H4 grid.
  G5 IS only — seal at 2024-05-02 (is_ticks span).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "research" / "code"))
import arctic_io as aio          # noqa: E402

# pre-registered ladder (shared with gate2_interaction)
K_RUNGS      = 9
LADDER_BARS  = [2 ** k for k in range(K_RUNGS)]     # 1,2,4,..,256 M5 bars
M5_PER_H4    = 48                                    # 240 min / 5
HORIZON_BARS = M5_PER_H4                             # H4 forward label
WARMUP_H4    = 250                                   # expanding-stat warmup (H4 obs)
RCOLS = [f"r{k}" for k in range(K_RUNGS)]
ZCOLS = [f"z{k}" for k in range(K_RUNGS)]
CACHE = REPO / "research" / "outputs" / "msm_features_full.pkl"


def build_m5_closes() -> pd.Series:
    """SORTED M5 mid-close over the IS span (G1, G5), month-by-month, below the seal."""
    seal = aio.seal_date()
    frames = []
    for ym in tqdm(aio.tick_months(), desc="M5 closes (IS)"):
        if pd.Timestamp(year=int(ym[0]), month=int(ym[1]), day=1) >= seal:
            continue
        df = aio.read_tick_month(ym, columns=["bid", "ask"], as_column=False)
        df = df[df.index < seal]
        if df.empty:
            continue
        mid = (df["bid"] + df["ask"]) * 0.5
        frames.append(mid.resample("5min").last().dropna())
    m5 = pd.concat(frames).sort_index()
    m5 = m5[~m5.index.duplicated(keep="first")]
    assert m5.index.is_monotonic_increasing, "M5 index non-monotonic — look-ahead risk"
    return m5.rename("close")


def build_features(m5: pd.Series) -> pd.DataFrame:
    """Full-ladder H4 feature frame: r0..r8, causal z0..z8, fwd label, price."""
    rr = {f"r{k}": m5 / m5.shift(L) - 1.0 for k, L in enumerate(LADDER_BARS)}  # G2 past
    feat = pd.DataFrame(rr, index=m5.index)
    feat["fwd"] = m5.shift(-HORIZON_BARS) / m5 - 1.0                            # G4 label

    # H4 decision grid (top of hours 0,4,8,..)
    h4 = feat[(feat.index.minute == 0) & (feat.index.hour % 4 == 0)].copy()
    h4 = h4.dropna(subset=RCOLS + ["fwd"])

    # G3 causal standardisation per rung (expanding to t-1)
    z = pd.DataFrame(index=h4.index)
    for c in RCOLS:
        mu = h4[c].expanding(min_periods=WARMUP_H4).mean().shift(1)
        sd = h4[c].expanding(min_periods=WARMUP_H4).std().shift(1)
        z[f"z{c[1:]}"] = (h4[c] - mu) / sd
    z = z.dropna()
    h4 = h4.loc[z.index]
    h4[ZCOLS] = z[ZCOLS]
    h4["price"] = m5.loc[h4.index].values
    return h4[RCOLS + ZCOLS + ["fwd", "price"]].dropna()


def load() -> pd.DataFrame:
    """Read the cached full-ladder frame (build first if missing)."""
    if not CACHE.exists():
        raise FileNotFoundError(f"{CACHE} missing — run features.py once to build it.")
    return pd.read_pickle(CACHE)


def run():
    m5 = build_m5_closes()
    feat = build_features(m5)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    feat.to_pickle(CACHE)
    print("\n=== MSM-001 full-ladder feature cache ===")
    print(f"M5 bars: {len(m5):,}   span {m5.index[0]} -> {m5.index[-1]}")
    print(f"H4 decision obs (post-warmup): {len(feat):,}")
    print(f"fwd H4: mean {feat['fwd'].mean():+.5f}  std {feat['fwd'].std():.5f}")
    print(f"cached -> {CACHE}")


if __name__ == "__main__":
    run()
