"""IBKR TWS safe limit order test — GLD BUY LMT far below market, paper account. Won't fill."""
from ib_async import LimitOrder
from _common import connect, gld_contract, last_price, wait_for_status

ib = connect(client_id=4)
try:
    contract = gld_contract(ib)
    ref_price = last_price(ib, contract)
    limit_price = round(ref_price * 0.5, 2)
    print(f"Reference price: {ref_price}  Limit price (50% below): {limit_price}")

    order = LimitOrder('BUY', 1, limit_price)
    trade = ib.placeOrder(contract, order)
    wait_for_status(ib, trade, {'Submitted', 'PreSubmitted'})

    input("Check TWS now — confirm a resting BUY LMT GLD order at "
          f"{limit_price} appears, then press Enter to cancel...")

    ib.cancelOrder(order)
    wait_for_status(ib, trade, {'Cancelled', 'ApiCancelled'})
    print(f"Final status: {trade.orderStatus.status}")
except Exception as e:
    print(f"ERROR: {e}")
    print("Check TWS manually for any open orders before re-running.")
    raise
finally:
    ib.disconnect()
    print("Disconnected.")
