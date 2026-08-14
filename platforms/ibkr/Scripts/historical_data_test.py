"""IBKR TWS historical data test — GLD daily bars, paper account."""
from _common import connect, gld_contract

ib = connect(client_id=2)
try:
    contract = gld_contract(ib)
    bars = ib.reqHistoricalData(
        contract, endDateTime='', durationStr='30 D',
        barSizeSetting='1 day', whatToShow='TRADES', useRTH=True,
    )
    print(f"Bars returned: {len(bars)}")
    for bar in bars:
        print(bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume)
except Exception as e:
    print(f"ERROR: {e}")
    raise
finally:
    ib.disconnect()
    print("Disconnected.")
