"""
Export research parquet ticks -> a compact binary the MQL5 import script reads to
build an MT5 custom symbol with the EXACT ticks the Python research used (so the
Strategy Tester runs on identical data = a VALID Gate-7 FIDELITY test).

Binary layout (little-endian, the x64 MT5 native order):
    header:  int64  n_ticks
    record:  int64  time_msc   (epoch milliseconds, UTC)
             float64 bid
             float64 ask
             int64  volume
Record size = 32 bytes. The MQL5 side reads count then loops FileReadLong/Double.

Writes to MT5 Common\\Files so import_custom_ticks.mq5 (FILE_COMMON) can read it.
Round-trip self-test runs before exit (re-reads the file, checks first/last tick).

    python -X utf8 research/code/export_ticks_mt5.py 2024-05          # one month (validation)
    python -X utf8 research/code/export_ticks_mt5.py 2024-05 2026-05  # range (full OOS)
"""
from __future__ import annotations
import os
import sys
import struct
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files
from research.code.arctic_io import read_tick_month

COMMON = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files"
OUT_BIN = COMMON / "baysix_XAUUSD_pq_ticks.bin"
REC = struct.Struct("<qddq")   # time_msc, bid, ask, volume
# structured dtype with the SAME little-endian byte layout as REC (vectorised write)
RECDT = np.dtype([("t", "<i8"), ("b", "<f8"), ("a", "<f8"), ("v", "<i8")])

# Gate-7 fidelity: replace the parquet's NATIVE Dukascopy spread (~5-pip / $0.50 at the
# 09:00 open) with the 2-pip JM spread Python validated on (anchor_oos.py SPREAD=2*0.10).
# Each tick becomes bid/ask = parquet_mid +/- HALF_SPREAD, so the tester pays exactly the
# $0.20 modeled cost (and the EA's bid-based OR sits symmetric to Python's mid OR). The
# real JM venue spread is measured later at the FORWARD gate, not here.
HALF_SPREAD = 0.10   # half of the 2-pip XAUUSD spread (1 pip = $0.10/oz)


def _months(a: str, b: str | None) -> list[tuple[int, int]]:
    y0, m0 = int(a[:4]), int(a[5:7])
    y1, m1 = (int(b[:4]), int(b[5:7])) if b else (y0, m0)
    out = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: export_ticks_mt5.py YYYY-MM [YYYY-MM]")
    months = _months(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    files = _tick_files(months)
    if not files:
        sys.exit(f"no parquet tick files for {months}")
    COMMON.mkdir(parents=True, exist_ok=True)

    n = 0
    first = last = None
    with open(OUT_BIN, "wb") as fh:
        fh.write(struct.pack("<q", 0))   # placeholder count
        for f in files:
            df = read_tick_month(f, columns=["ts_utc", "bid", "ask", "volume"])
            msc = (df["ts_utc"].values.astype("datetime64[ms]").astype(np.int64))
            mid = (df["bid"].values.astype(np.float64) + df["ask"].values.astype(np.float64)) * 0.5
            bid = mid - HALF_SPREAD   # synthesize 2-pip JM spread (see HALF_SPREAD note)
            ask = mid + HALF_SPREAD
            vol = np.nan_to_num(df["volume"].values, nan=0.0).astype(np.int64)
            arr = np.empty(len(df), dtype=RECDT)
            arr["t"] = msc; arr["b"] = bid; arr["a"] = ask; arr["v"] = vol
            fh.write(arr.tobytes())
            n += len(df)
            if first is None and len(df):
                first = (int(msc[0]), float(bid[0]), float(ask[0]))
            if len(df):
                last = (int(msc[-1]), float(bid[-1]), float(ask[-1]))
            print(f"  {Path(f).parent.name}: +{len(df):,} ticks (total {n:,})")
        fh.seek(0)
        fh.write(struct.pack("<q", n))   # real count

    size_mb = OUT_BIN.stat().st_size / 1e6
    print(f"\n[ok] wrote {n:,} ticks -> {OUT_BIN}  ({size_mb:.1f} MB)")
    print(f"     first {pd.Timestamp(first[0],unit='ms')} bid={first[1]} ask={first[2]}")
    print(f"     last  {pd.Timestamp(last[0],unit='ms')} bid={last[1]} ask={last[2]}")

    # round-trip self-test: re-read header + first + last record
    with open(OUT_BIN, "rb") as fh:
        (cnt,) = struct.unpack("<q", fh.read(8))
        r0 = REC.unpack(fh.read(REC.size))
        fh.seek(8 + (cnt - 1) * REC.size)
        rN = REC.unpack(fh.read(REC.size))
    ok = (cnt == n and r0[:3] == (first[0], first[1], first[2])
          and rN[0] == last[0] and abs(rN[1] - last[1]) < 1e-9)
    print(f"     self-test: count={cnt:,} first/last match -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit("round-trip self-test FAILED — do not run the MQL5 import")


if __name__ == "__main__":
    main()
