"""
Resample XAUUSD Dukascopy ticks -> D1 / H4 / H1 bars for the B2B engine.

Convention (LOCKED 2026-06-03, to match the live JustMarkets MT5 EA):
  - Bar boundaries on GMT+3 server time   (D1 closes 21:00 UTC)
  - close = last BID in the interval        (MT5 CopyRates OHLC is bid-based)
  - timeframes: D1 + H4 + H1 ONLY

IS/OOS seal: 2024-05-02 (inclusive = IS). OOS files are written but must stay
sealed until Gate 6 (protocol rule 6, one-shot).

Output: data/parquet/bars/xauusd_{tf}_gmt3_bid_{is,oos}.parquet  (cols: time, close, n_ticks)

Run in a NEW PowerShell window (long job, ~3GB ticks) so output is live:
  Start-Process powershell -ArgumentList '-NoExit','-Command',
    'cd <repo>; python b2b/backtest/resample_bars.py'
"""
import glob
import os
import sys
import time

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:                      # graceful fallback
    def tqdm(x, **k):
        return x

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TICK_DIR = os.path.join(REPO, "data", "parquet", "CS-GOLD-DUKAS-TICK")
OUT_DIR = os.path.join(REPO, "data", "parquet", "bars")

GMT_OFFSET = pd.Timedelta(hours=3)       # server = UTC+3
SEAL = pd.Timestamp("2024-05-02")        # IS inclusive; OOS strictly after
TFS = {"d1": "1D", "h4": "4h", "h1": "1h"}


def reduce_file(path, accum):
    """Resample one tick partition into per-bar last-bid, merge into accum."""
    df = pd.read_parquet(path, columns=["ts_utc", "bid"])
    if df.empty:
        return
    df["server"] = pd.to_datetime(df["ts_utc"]) + GMT_OFFSET
    df = df.sort_values("ts_utc")
    for tf, freq in TFS.items():
        key = df["server"].dt.floor(freq)
        g = pd.DataFrame({"time": key, "ts_utc": df["ts_utc"].values,
                          "bid": df["bid"].values})
        # last bid (by ts) per bar, plus tick count
        last = g.groupby("time").agg(ts_utc=("ts_utc", "last"),
                                     close=("bid", "last"),
                                     n_ticks=("bid", "size"))
        accum[tf].append(last.reset_index())


def finalize(tf_frames):
    """Combine per-file partials; for bars split across files keep latest tick."""
    out = {}
    for tf, parts in tf_frames.items():
        if not parts:
            out[tf] = pd.DataFrame(columns=["time", "close", "n_ticks"])
            continue
        allp = pd.concat(parts, ignore_index=True).sort_values("ts_utc")
        # boundary bars appear in >1 file -> keep the last tick, sum tick counts
        agg = allp.groupby("time").agg(close=("close", "last"),
                                       n_ticks=("n_ticks", "sum"))
        out[tf] = agg.reset_index().sort_values("time").reset_index(drop=True)
    return out


def main():
    files = sorted(glob.glob(os.path.join(TICK_DIR, "year=*", "**", "*.parquet"),
                             recursive=True))
    print(f"[resample] {len(files)} tick partitions under {TICK_DIR}")
    if not files:
        sys.exit("No tick parquet files found.")

    os.makedirs(OUT_DIR, exist_ok=True)
    accum = {tf: [] for tf in TFS}

    t0 = time.time()
    for path in tqdm(files, desc="ticks->bars", unit="file"):
        reduce_file(path, accum)
        print(f"  done {os.path.relpath(path, TICK_DIR)}  "
              f"({time.time() - t0:.0f}s elapsed)", flush=True)

    bars = finalize(accum)

    print("\n[resample] writing IS/OOS splits at seal", SEAL.date())
    for tf, df in bars.items():
        is_df = df[df["time"] < SEAL + pd.Timedelta(days=1)]
        oos_df = df[df["time"] >= SEAL + pd.Timedelta(days=1)]
        for tag, part in (("is", is_df), ("oos", oos_df)):
            fp = os.path.join(OUT_DIR, f"xauusd_{tf}_gmt3_bid_{tag}.parquet")
            part.to_parquet(fp, index=False)
        rng = (df["time"].min(), df["time"].max())
        print(f"  {tf.upper():3} total={len(df):>7}  IS={len(is_df):>7}  "
              f"OOS={len(oos_df):>7}  range {rng[0]} -> {rng[1]}")

    print(f"\n[resample] DONE in {time.time() - t0:.0f}s -> {OUT_DIR}")


if __name__ == "__main__":
    main()
