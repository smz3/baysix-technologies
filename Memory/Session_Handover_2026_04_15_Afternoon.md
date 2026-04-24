# Session Handover — April 15, 2026 (Afternoon — LEAN Phase 2B/2C near-complete, one fix remaining)

## What Was Accomplished This Session

### LEAN CLI Phase 2A + 2B + 2C — Fully Built, One Fix From Done

All infrastructure is in place. A full end-to-end backtest ran. One data format bug was diagnosed and fixed but NOT yet validated.

---

### What Is Built

| Component | File | Status |
|-----------|------|--------|
| LEAN workspace | `workspace/sigma-lean/lean.json` | Done |
| QCAlgorithm strategy | `workspace/sigma-lean/B2BZoneStrategy/main.py` | Done |
| sigma_core in Docker | `workspace/sigma-lean/B2BZoneStrategy/sigma_core/` | Done |
| Data converter | `workspace/sigma-lean/scripts/parquet_to_lean.py` | Done (see bug below) |
| Market hours DB | `workspace/sigma-lean/data/market-hours/market-hours-database.json` | Done |
| Symbol properties | `workspace/sigma-lean/data/symbol-properties/symbol-properties-database.csv` | Done |
| LEAN data (H1 + D1) | `workspace/sigma-lean/data/crypto/binance/hour/` etc. | Done — needs rebuild after fix |

---

### The One Remaining Bug — Quote Bar Column Mismatch

**Error observed in last backtest run:**
```
QuoteBar.Reader(): Error parsing stream, Symbol: BTCUSDT, Resolution: Hour
System.FormatException: String '46650.00' was not recognized as a valid DateTime.
```

**Root cause (confirmed from LEAN source `QuoteBar.cs`):**

LEAN's `ParseQuote()` StreamReader version for Hour/Daily resolution expects **11 columns**:
```
time, bidO, bidH, bidL, bidC, lastBidSize, askO, askH, askL, askC, lastAskSize
```

My previous quote CSV had **9 columns** (missing `lastBidSize` at col 5 and `lastAskSize` at col 10). This caused the StreamReader to consume fields from the **next row** on each parse, creating a cascade where `GetDateTime()` read a price value instead of a timestamp.

**Fix already applied** (last action of this session) in `parquet_to_lean.py` line ~54:
```python
# BEFORE (wrong — 9 cols, missing size columns):
rows.append(f"{t},{o},{h},{l},{c},{o},{h},{l},{c}")

# AFTER (correct — 11 cols, size = volume):
rows.append(f"{t},{o},{h},{l},{c},{v},{o},{h},{l},{c},{v}")
```

**This fix is in the file but the data has NOT been rebuilt and the backtest has NOT been re-run.**

---

### Last Backtest Result (with broken quote bars — for reference)

Ran: `lean backtest "B2BZoneStrategy"` from `workspace/sigma-lean/`
- **Period:** 2024-01-01 to 2024-03-31 (3 months)
- **Data points:** 2,119 H1 bars processed
- **Zones detected:** 54 zones on first bar (warmup), 57 by bar 15
- **Trades:** 2 trades taken
  - Trade 1: BULLISH entry 42436.60, TP at 2R = 43165.79 — hit TP correctly ✓
  - Trade 2: BEARISH entry 43556.20, sl=44311, tp=42045 — fill price was ₮20240101 (catastrophic — caused by quote bar bug) ✗
- **Outcome:** Margin call at bar 16, portfolio went to -$26M — caused entirely by the quote bar bug

Once the quote bar bug is fixed, trades should fill at correct market prices.

---

## Exact Next Steps — Resume From Here

### Step 1 — Rebuild LEAN data with fixed quote format

```bash
cd workspace/sigma-lean
rm -rf data/crypto
python scripts/parquet_to_lean.py
```

Expected output:
- 35,064 H1 bars for btcusdt_trade.zip and btcusdt_quote.zip
- 677 D1 bars for daily zips
- usdtusd files created for Coinbase

Verify quote zip has 11 columns:
```python
import zipfile
with zipfile.ZipFile('data/crypto/binance/hour/btcusdt_quote.zip') as zf:
    with zf.open(zf.namelist()[0]) as f:
        print(f.read().decode().splitlines()[0])
# Should show: 20220101 00:00,46210.57,46729.73,46210.55,46650.01,8957.4650,46210.57,46729.73,46210.55,46650.01,8957.4650
```

### Step 2 — Run the backtest

```bash
cd workspace/sigma-lean
lean backtest "B2BZoneStrategy"
```

Expected: No more `QuoteBar.Reader()` errors. Trades fill at correct prices (e.g., ~43000-45000 range for Jan 2024 BTC). Zone detection working (54+ zones on first bar). Multiple ENTRY/EXIT logs in the backtest log file.

### Step 3 — Review results

Look at:
- `B2BZoneStrategy/backtests/<latest>/1698272679-log.txt` — ENTRY/EXIT trade log
- `B2BZoneStrategy/backtests/<latest>/1698272679-summary.json` — P&L, Sharpe, drawdown

Check for:
- Fill prices in correct range (~40k-70k for Jan-Mar 2024 BTC)
- SL/TP hits making sense (2R)
- No margin call errors

---

## Architecture Summary (for reference)

### How sigma_core gets into LEAN Docker

LEAN Docker mounts the PROJECT directory (`B2BZoneStrategy/`) as `/LeanCLI` — NOT the workspace root. So `sigma_core` must be inside the project directory. It is:
```
B2BZoneStrategy/
├── main.py
├── sigma_core/        ← full copy of pure-Python source
│   └── b2b/
│       ├── detectors/
│       │   ├── swing_points.py
│       │   ├── b2b_engine.py
│       │   └── zone_status.py
│       ├── filters/
│       └── models/
│           └── structures.py
└── config.json
```

### sys.path fix in main.py (lines 29-33)

```python
for candidate in ["/LeanCLI", os.path.dirname(__file__), "."]:
    if os.path.isdir(os.path.join(candidate, "sigma_core")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
        break
```

### LEAN data format confirmed (Hour/Daily)

| File | Path | Columns |
|------|------|---------|
| Trade | `data/crypto/binance/hour/btcusdt_trade.zip` | `YYYYMMDD HH:mm,O,H,L,C,V` |
| Quote | `data/crypto/binance/hour/btcusdt_quote.zip` | `YYYYMMDD HH:mm,bO,bH,bL,bC,bSz,aO,aH,aL,aC,aSz` |
| USDT | `data/crypto/coinbase/hour/usdtusd_trade.zip` | same 6-col trade format, price=1.0 |

Single flat zip, single CSV entry: `{symbol}_{ticktype}.csv`. RAW prices (no × 10000).

### Strategy config (main.py)

- Start: 2024-01-01, End: 2024-03-31 (3-month test)
- Cash: $100,000
- Symbol: BTCUSDT, Binance, Hour resolution
- Warmup: 500 bars (H1)
- DetectionConfig: swing_window=3, swing_lookback=20, min_age_bars=8
- Entry: L1 touch (low <= L1 bullish, high >= L1 bearish)
- SL: L2 ± 0.3% buffer
- TP: 2R

---

## Still Open (Not This Session's Work)

- **OQ-003** — slippage sweep (blocks Test 13A CIO approval). Script: `workspace/sigma-crypto/scripts/run_phase_4_simulation.py`
- **sigma-research Cloud Run** — still blocked on org policy. See `DEPLOYMENT_HANDOVER.md`
- **Phase 2D** — LEAN vs VectorizedBacktester cross-validation (after backtest confirms correct fills)
- **Phase 2E** — Live Binance execution (future)
- **Vault Phase 3** stubs still empty

---

## Key Files

| Path | Purpose |
|------|---------|
| `workspace/sigma-lean/scripts/parquet_to_lean.py` | Data converter — fix applied, needs rebuild run |
| `workspace/sigma-lean/B2BZoneStrategy/main.py` | QCAlgorithm strategy |
| `workspace/sigma-lean/B2BZoneStrategy/config.json` | LEAN project config |
| `workspace/sigma-lean/lean.json` | LEAN workspace config |
| `C:\Users\User\.claude\plans\snoopy-orbiting-breeze.md` | Full Phase 2 plan |
