"""
MT5 <-> Python bridge: pull JustMarkets OHLC bars (D1/H4/H1) into Python.

Uses the MetaTrader5 package to talk to the RUNNING terminal (read-only here --
only copy_rates, no trading). These are the broker's actual bars: the exact
input the live EA sees, WITH high/low (so we get the full lifecycle, not just
close). This is the parity source; the Dukascopy resample stays the deep-history
backtest source.

Symbol: XAUUSD.s (JustMarkets '.s' suffix). Bar 'time' is server time (GMT+3),
returned naive. Requires the terminal open with Algo Trading enabled.

Output: data/parquet/bars/mt5/xauusd_{tf}_mt5.parquet
        cols: time, open, high, low, close, tick_volume, spread
"""
import os

import pandas as pd
import MetaTrader5 as mt5

SYMBOL = "XAUUSD.s"
TFS = {"d1": mt5.TIMEFRAME_D1, "h4": mt5.TIMEFRAME_H4, "h1": mt5.TIMEFRAME_H1}
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   "..", "..", "data", "parquet", "bars", "mt5"))
COUNT = 50000   # > available for D1/H4/H1, < the terminal's ~65k per-call cap


def main():
    if not mt5.initialize():
        raise SystemExit(f"initialize failed: {mt5.last_error()}")
    ti, ai = mt5.terminal_info(), mt5.account_info()
    print(f"[bridge] terminal={ti.company} connected={ti.connected} "
          f"server={ai.server if ai else '?'}")

    if not mt5.symbol_select(SYMBOL, True):
        mt5.shutdown()
        raise SystemExit(f"symbol_select {SYMBOL} failed: {mt5.last_error()}")

    os.makedirs(OUT, exist_ok=True)
    for tf, code in TFS.items():
        rates = mt5.copy_rates_from_pos(SYMBOL, code, 0, COUNT)
        if rates is None or len(rates) == 0:
            print(f"  {tf.upper()}: NO DATA ({mt5.last_error()})")
            continue
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")   # server time (GMT+3), naive
        df = df[["time", "open", "high", "low", "close", "tick_volume", "spread"]]
        fp = os.path.join(OUT, f"xauusd_{tf}_mt5.parquet")
        df.to_parquet(fp, index=False)
        print(f"  {tf.upper()}: {len(df):>7} bars  "
              f"{df.time.min()} -> {df.time.max()}  -> {os.path.basename(fp)}")

    mt5.shutdown()
    print(f"[bridge] done -> {OUT}")


if __name__ == "__main__":
    main()
