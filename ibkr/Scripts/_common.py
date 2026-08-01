"""Shared connect helper + GLD contract for ibkr/Scripts/ test steps 1-4.
Not a standalone script — import only."""
from ib_async import IB, Stock

HOST = '127.0.0.1'
PORT = 7497  # TWS paper trading port

def connect(client_id: int) -> IB:
    ib = IB()
    ib.errorEvent += lambda reqId, code, msg, contract: print(f"[TWS {code}] {msg}")
    ib.connect(HOST, PORT, clientId=client_id)
    print("Connected:", ib.isConnected(), "| Accounts:", ib.managedAccounts())
    return ib

def gld_contract(ib: IB) -> Stock:
    contract = Stock('GLD', 'SMART', 'USD')
    ib.qualifyContracts(contract)
    return contract

def last_price(ib: IB, contract, timeout: int = 10) -> float:
    """Delayed snapshot price, used by steps 3-4 to size a safe limit price."""
    ib.reqMarketDataType(3)
    ticker = ib.reqMktData(contract, '', False, False)
    price = None
    for _ in range(timeout):
        ib.sleep(1)
        candidate = ticker.last if ticker.last == ticker.last else ticker.close
        if candidate and candidate == candidate:
            price = candidate
            break
    ib.cancelMktData(contract)
    return price

def wait_for_status(ib: IB, trade, targets: set, timeout: int = 15) -> str:
    """Poll trade.orderStatus.status, printing each transition, until it
    reaches one of `targets` or timeout elapses."""
    seen = None
    for _ in range(timeout):
        ib.sleep(1)
        status = trade.orderStatus.status
        if status != seen:
            print(f"Order status: {status}")
            seen = status
        if status in targets:
            break
    return trade.orderStatus.status
