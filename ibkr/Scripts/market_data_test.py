"""IBKR TWS delayed market data snapshot test — GLD, paper account (no live data subscription)."""
from _common import connect, gld_contract

ib = connect(client_id=3)
try:
    contract = gld_contract(ib)
    ib.reqMarketDataType(3)  # 3 = delayed (no real-time subscription on this account)
    ticker = ib.reqMktData(contract, '', False, False)
    for _ in range(10):
        ib.sleep(1)
        if ticker.last == ticker.last or ticker.close == ticker.close:  # NaN check
            break
    print(f"Last: {ticker.last}  Bid: {ticker.bid}  Ask: {ticker.ask}  Close: {ticker.close}")
    print("Confirm above a nonzero price arrived, and check stdout for a "
          "'[TWS 10167] ... delayed market data' line confirming delayed mode.")
    ib.cancelMktData(contract)
except Exception as e:
    print(f"ERROR: {e}")
    raise
finally:
    ib.disconnect()
    print("Disconnected.")
