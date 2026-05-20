"""
parquet_to_lean.py
==================
Converts BTCUSDT parquet files (sigma-crypto format) -> LEAN CLI local data format.

Official LEAN data format (v2.5, from QuantConnect docs):
  Hour/Daily resolution:
    - Single flat zip:  data/crypto/{market}/{resolution}/{symbol}_{ticktype}.zip
    - Single CSV entry: {symbol}_{ticktype}.csv   (no date prefix)
    - Time column:      YYYYMMDD HH:mm  (UTC datetime string)
    - Prices:           RAW (not scaled) for Hour/Daily resolution

  Minute/Second resolution (not used here):
    - Per-day zips in subdir, time = ms from midnight, prices * scale

Usage
-----
  cd workspace/sigma-lean
  python scripts/parquet_to_lean.py [--start YYYY-MM-DD] [--end YYYY-MM-DD]
"""

import argparse
import zipfile
from pathlib import Path

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
def build_trade_csv(df: pd.DataFrame, symbol: str, tick_type: str = "trade") -> tuple:
    """
    Return (entry_name, csv_content) for ALL bars in df.
    entry_name : {symbol}_{tick_type}.csv  (no date — flat single entry)
    Time       : YYYYMMDD HH:mm  (UTC)
    Prices     : raw floats, 2 dp
    Trade cols : time, open, high, low, close, volume
    Quote cols : time, bidopen, bidhigh, bidlow, bidclose, askopen, askhigh, asklow, askclose
    """
    entry_name = f"{symbol}_{tick_type}.csv"
    rows = []

    for _, row in df.iterrows():
        ts  = pd.Timestamp(row["time"])
        t   = ts.strftime("%Y%m%d %H:%M")
        o   = f"{row['open']:.2f}"
        h   = f"{row['high']:.2f}"
        l   = f"{row['low']:.2f}"
        c   = f"{row['close']:.2f}"
        v   = f"{row['volume']:.4f}"

        if tick_type == "quote":
            # bid = ask = mid (zero spread for backtesting)
            # Format: time,bidO,bidH,bidL,bidC,lastBidSize,askO,askH,askL,askC,lastAskSize
            rows.append(f"{t},{o},{h},{l},{c},{v},{o},{h},{l},{c},{v}")
        else:
            rows.append(f"{t},{o},{h},{l},{c},{v}")

    return entry_name, "\n".join(rows) + "\n"


def write_flat_zip(df: pd.DataFrame, zip_path: Path, symbol: str, tick_type: str):
    """Write single flat zip with one CSV entry covering all dates."""
    entry_name, csv_content = build_trade_csv(df, symbol, tick_type)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(entry_name, csv_content)
    print(f"    {zip_path.name}  ({len(df)} bars, entry={entry_name})")


def write_usdtusd_zip(df: pd.DataFrame, zip_path: Path, symbol: str = "usdtusd"):
    """
    Write USDT/USD conversion rate = 1.0 throughout.
    LEAN needs this to value the USDT account balance in USD.
    """
    entry_name = f"{symbol}_trade.csv"
    rows = []
    for _, row in df.iterrows():
        t = pd.Timestamp(row["time"]).strftime("%Y%m%d %H:%M")
        rows.append(f"{t},1.00,1.00,1.00,1.00,1000000.00")
    csv_content = "\n".join(rows) + "\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(entry_name, csv_content)
    print(f"    {zip_path.name}  (USDT/USD=1.0, {len(df)} bars)")


# ─────────────────────────────────────────────────────────────────────────────
def convert_hourly(src_path: Path, dst_root: Path, start: pd.Timestamp, end: pd.Timestamp):
    print(f"\nH1: Reading {src_path.name} ...")
    df = pd.read_parquet(src_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df[(df["time"] >= start) & (df["time"] <= end)].copy()
    print(f"  {len(df)} bars  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]})")

    # Binance BTCUSDT
    out = dst_root / "crypto" / "binance" / "hour"
    out.mkdir(parents=True, exist_ok=True)
    write_flat_zip(df, out / "btcusdt_trade.zip", "btcusdt", "trade")
    write_flat_zip(df, out / "btcusdt_quote.zip", "btcusdt", "quote")

    # Coinbase USDT/USD (currency conversion feed)
    usdt_h = dst_root / "crypto" / "coinbase" / "hour"
    usdt_h.mkdir(parents=True, exist_ok=True)
    write_usdtusd_zip(df, usdt_h / "usdtusd_trade.zip")


def convert_daily(src_path: Path, dst_root: Path, start: pd.Timestamp, end: pd.Timestamp):
    print(f"\nD1: Reading {src_path.name} ...")
    df = pd.read_parquet(src_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df[(df["time"] >= start) & (df["time"] <= end)].copy()
    print(f"  {len(df)} bars  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]})")

    # Binance BTCUSDT
    out = dst_root / "crypto" / "binance" / "daily"
    out.mkdir(parents=True, exist_ok=True)
    write_flat_zip(df, out / "btcusdt_trade.zip", "btcusdt", "trade")
    write_flat_zip(df, out / "btcusdt_quote.zip", "btcusdt", "quote")

    # Coinbase USDT/USD
    usdt_d = dst_root / "crypto" / "coinbase" / "daily"
    usdt_d.mkdir(parents=True, exist_ok=True)
    write_usdtusd_zip(df, usdt_d / "usdtusd_trade.zip")


# ─────────────────────────────────────────────────────────────────────────────
def write_market_hours(dst_root: Path):
    mh_dir  = dst_root / "market-hours"
    mh_dir.mkdir(parents=True, exist_ok=True)
    mh_path = mh_dir / "market-hours-database.json"
    if mh_path.exists():
        print("  market-hours-database.json exists -- skipping")
        return
    mh_path.write_text("""{
  "entries": {
    "Crypto-Binance-[*]": {
      "dataTimeZone": "UTC",
      "exchangeTimeZone": "UTC",
      "monday":    [{"start":"00:00:00","end":"1.00:00:00"}],
      "tuesday":   [{"start":"00:00:00","end":"1.00:00:00"}],
      "wednesday": [{"start":"00:00:00","end":"1.00:00:00"}],
      "thursday":  [{"start":"00:00:00","end":"1.00:00:00"}],
      "friday":    [{"start":"00:00:00","end":"1.00:00:00"}],
      "saturday":  [{"start":"00:00:00","end":"1.00:00:00"}],
      "sunday":    [{"start":"00:00:00","end":"1.00:00:00"}],
      "holidays":  []
    },
    "Crypto-Coinbase-[*]": {
      "dataTimeZone": "UTC",
      "exchangeTimeZone": "UTC",
      "monday":    [{"start":"00:00:00","end":"1.00:00:00"}],
      "tuesday":   [{"start":"00:00:00","end":"1.00:00:00"}],
      "wednesday": [{"start":"00:00:00","end":"1.00:00:00"}],
      "thursday":  [{"start":"00:00:00","end":"1.00:00:00"}],
      "friday":    [{"start":"00:00:00","end":"1.00:00:00"}],
      "saturday":  [{"start":"00:00:00","end":"1.00:00:00"}],
      "sunday":    [{"start":"00:00:00","end":"1.00:00:00"}],
      "holidays":  []
    }
  }
}
""")
    print(f"  Wrote {mh_path}")


def write_symbol_properties(dst_root: Path):
    sp_dir  = dst_root / "symbol-properties"
    sp_dir.mkdir(parents=True, exist_ok=True)
    sp_path = sp_dir / "symbol-properties-database.csv"
    if sp_path.exists():
        print("  symbol-properties-database.csv exists -- skipping")
        return
    sp_path.write_text(
        "market,symbol,description,quoteCurrency,contractMultiplier,"
        "minimumPriceVariation,lotSize,marketTicker,minimumOrderSize,priceMagnifier\n"
        "binance,BTCUSDT,Bitcoin vs Tether,USDT,1,0.01,0.000001,BTCUSDT,0.000001,1\n"
        "coinbase,USDTUSD,Tether USD,USD,1,0.0001,1,USDTUSD,1,1\n"
    )
    print(f"  Wrote {sp_path}")


# ─────────────────────────────────────────────────────────────────────────────
def convert_minute(src_path: Path, dst_root: Path, start: pd.Timestamp, end: pd.Timestamp):
    """
    Convert any sub-hour parquet (M30/M15/M5/M1) to LEAN minute/ per-day ZIP format.

    LEAN minute/ layout:
      data/crypto/binance/minute/btcusdt/YYYYMMDD_trade.zip
        └── btcusdt_trade.csv  (one bar per line, time = ms from midnight)
    """
    print(f"\nMinute: Reading {src_path.name} ...")
    df = pd.read_parquet(src_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df[(df["time"] >= start) & (df["time"] <= end)].copy()
    print(f"  {len(df):,} bars  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]})")

    # Pre-compute ms-from-midnight (vectorized)
    df["date"]     = df["time"].dt.date
    df["midnight"] = df["time"].dt.normalize()
    df["ms"]       = ((df["time"] - df["midnight"]).dt.total_seconds() * 1000).astype("int64")

    out      = dst_root / "crypto" / "binance" / "minute" / "btcusdt"
    usdt_out = dst_root / "crypto" / "coinbase" / "minute" / "usdtusd"
    out.mkdir(parents=True, exist_ok=True)
    usdt_out.mkdir(parents=True, exist_ok=True)

    days_written = 0
    for date, grp in df.groupby("date"):
        date_str = date.strftime("%Y%m%d")

        # BTCUSDT trade
        lines = (
            grp["ms"].astype(str) + "," +
            grp["open"].round(2).astype(str) + "," +
            grp["high"].round(2).astype(str) + "," +
            grp["low"].round(2).astype(str) + "," +
            grp["close"].round(2).astype(str) + "," +
            grp["volume"].round(4).astype(str)
        )
        csv_content = "\n".join(lines) + "\n"
        with zipfile.ZipFile(out / f"{date_str}_trade.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("btcusdt_trade.csv", csv_content)

        # Coinbase USDT/USD = 1.0 at minute resolution
        usdt_lines = grp["ms"].astype(str) + ",1.00,1.00,1.00,1.00,1000000.00"
        usdt_csv   = "\n".join(usdt_lines) + "\n"
        with zipfile.ZipFile(usdt_out / f"{date_str}_trade.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("usdtusd_trade.csv", usdt_csv)

        days_written += 1
        if days_written % 365 == 0:
            print(f"    ... {days_written} days written")

    print(f"    minute/ : {days_written} daily ZIPs written  ({src_path.stem})")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-h1", default=str(
        Path(__file__).parent.parent.parent / "sigma-crypto" / "data" / "raw" / "BTCUSDT_H1.parquet"))
    parser.add_argument("--src-d1", default=str(
        Path(__file__).parent.parent.parent / "sigma-crypto" / "data" / "raw" / "BTCUSDT_D1.parquet"))
    parser.add_argument("--src-m30", default=str(
        Path(__file__).parent.parent.parent / "sigma-crypto" / "data" / "raw" / "BTCUSDT_M30.parquet"))
    parser.add_argument("--dst",   default=str(Path(__file__).parent.parent / "data"))
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end",   default="2025-12-31")
    args = parser.parse_args()

    dst_root = Path(args.dst)
    start    = pd.Timestamp(args.start)
    end      = pd.Timestamp(args.end) + pd.Timedelta(days=1)

    print("=" * 60)
    print("parquet_to_lean  SIGMA -> LEAN data converter")
    print(f"  Output : {dst_root}")
    print(f"  Range  : {args.start} -> {args.end}")
    print("=" * 60)

    write_market_hours(dst_root)
    write_symbol_properties(dst_root)

    src_h1 = Path(args.src_h1)
    if src_h1.exists():
        convert_hourly(src_h1, dst_root, start, end)
    else:
        print(f"WARNING: H1 parquet not found: {src_h1}")

    src_d1 = Path(args.src_d1)
    if src_d1.exists():
        convert_daily(src_d1, dst_root, start, end)
    else:
        print(f"NOTE: D1 parquet not found -- skipping")

    src_m30 = Path(args.src_m30)
    if src_m30.exists():
        convert_minute(src_m30, dst_root, start, end)
    else:
        print(f"NOTE: M30 parquet not found -- skipping minute/ conversion")

    print("\nDone. Next: lean backtest 'B2BZoneStrategy'")


if __name__ == "__main__":
    main()
