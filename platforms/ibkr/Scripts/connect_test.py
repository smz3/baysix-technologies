"""IBKR TWS API connectivity test — paper account, port 7497."""
from ib_async import IB

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

print("Connected:", ib.isConnected())
print("Accounts:", ib.managedAccounts())

summary = ib.accountSummary()
for row in summary:
    if row.tag in ('NetLiquidation', 'AvailableFunds', 'BuyingPower'):
        print(f"{row.tag}: {row.value} {row.currency}")

ib.disconnect()
