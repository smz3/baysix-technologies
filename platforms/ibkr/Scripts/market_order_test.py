"""IBKR TWS market order round-trip test — 1 share GLD, paper account. Buys, confirms fill/position, flattens."""
from ib_async import MarketOrder
from _common import connect, gld_contract, wait_for_status

ib = connect(client_id=5)
try:
    contract = gld_contract(ib)

    buy = MarketOrder('BUY', 1)
    trade = ib.placeOrder(contract, buy)
    wait_for_status(ib, trade, {'Filled'})
    print(f"Filled at avg price: {trade.orderStatus.avgFillPrice}")

    positions = [p for p in ib.positions() if p.contract.symbol == 'GLD']
    print("Positions:", positions)

    input("Confirm the GLD position appears in TWS, then press Enter to flatten...")

    sell = MarketOrder('SELL', 1)
    trade2 = ib.placeOrder(contract, sell)
    wait_for_status(ib, trade2, {'Filled'})
    print(f"Flattened at avg price: {trade2.orderStatus.avgFillPrice}")

    positions_after = [p for p in ib.positions() if p.contract.symbol == 'GLD']
    print("Positions after flatten:", positions_after)
except Exception as e:
    print(f"ERROR: {e}")
    print("Check TWS manually for any open position before re-running.")
    raise
finally:
    ib.disconnect()
    print("Disconnected.")
