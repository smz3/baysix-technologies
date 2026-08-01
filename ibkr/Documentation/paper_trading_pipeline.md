# IBKR Paper Trading Test Pipeline ("GOLDLOOP")

Task 283. Proves the full chain — paper account → TWS → API socket → Python
(`ib_async`) — works end to end, on GLD (SPDR gold ETF), before any real
strategy logic gets wired to it.

## Prerequisites

- TWS running, logged into the **paper** account (`DUR510878`, $1M simulated)
- API enabled: File → Global Configuration → API → Settings → "Enable
  ActiveX and Socket Clients"
- Socket port **7497** (TWS paper — do not confuse with 7496 live)
- `pip install -r ibkr/requirements.txt` (currently installed against
  **global Python**, not the repo's `.venv` — intentional for now, see
  Known Limitations)

## clientId table

Each script uses a distinct `clientId` so a stale connection from a previous
run never collides with the next one.

| Script | clientId |
|---|---|
| `connect_test.py` | 1 |
| `historical_data_test.py` | 2 |
| `market_data_test.py` | 3 |
| `limit_order_test.py` | 4 |
| `market_order_test.py` | 5 |

## Run order

Run each script directly, in this order, from `ibkr/Scripts/`:

1. **`connect_test.py`** — connects, prints account summary. Proves the
   base connection works.
2. **`historical_data_test.py`** — pulls 30 days of GLD daily bars. Proves
   historical data entitlement works (no subscription needed). Confirm
   ~20-22 bars printed with sane OHLCV values.
3. **`market_data_test.py`** — snapshots a delayed GLD quote. Proves live
   quote requests work without a real-time data subscription. Confirm a
   nonzero price AND a `[TWS 10167] ... delayed market data` line.
4. **`limit_order_test.py`** — places a BUY LMT GLD order 50% below market
   (zero fill risk), waits for you to confirm it in TWS, then cancels.
   Proves order routing + status polling work.
5. **`market_order_test.py`** — buys 1 share GLD at market, waits for your
   confirmation, then sells to flatten. Proves fills + position tracking +
   flattening work.

## Known limitations

- If a script crashes mid-flow (after placing an order, before
  cancelling/flattening), there is **no automatic cleanup** — check TWS
  manually for any open order or position before re-running.
- `ib_async` is installed in global Python, not this repo's `.venv`. Left
  as-is intentionally (not part of task 283's scope to force a `.venv`
  migration) — flagged as an open item, revisit if it causes friction.
- Market data is delayed (15-20 min), not real-time — no subscription
  exists on this account. Fine for pipeline testing; would need a paid
  subscription for latency-sensitive live use later.
- **IBKR runs a weekly system reset over the weekend** (observed: Saturday,
  confirmed via `Error 1100: Connectivity between IBKR and Trader Workstation
  has been lost`, repeating). TWS stays open locally and the API socket
  still accepts connections, but every request — including the account/
  position sync `ib_async` fires automatically on `connect()` — hangs or
  times out. All 5 scripts in this pipeline are unusable during this
  window; verify on a weekday or Sunday evening ET onward instead.
