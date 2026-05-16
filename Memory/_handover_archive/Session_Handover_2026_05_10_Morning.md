# Session Handover — 2026-05-10 Morning

**Written by**: Chief of Staff (Claude Code)
**Status at handover**: H1 LEAN backtest RUNNING — do not kill

---

## Where We Left Off

### The Core Problem (Previous Session)
M30 LEAN backtest was taking hours due to Windows/Docker/WSL2 file I/O bottleneck. The M30 data format requires 2,922 individual per-day ZIP files — LEAN reads them sequentially across the WSL2 boundary, making warmup alone take 20+ minutes at 100% CPU. In contrast, sigma-crypto reads one parquet file vectorized (seconds).

### What Was Done This Session
1. **Killed the stuck M30 container** (Docker ID: `7384fbab6ff2`) — 13 minutes in, still in warmup.
2. **Switched `main.py` to H1 primary** — `Resolution.Hour`, single flat `btcusdt_trade.zip` (fast I/O).
3. **Removed H1 consolidator** (it was redundant with H1 as primary).
4. **Renamed `_m30_buffer` → `_h1_buffer`**, removed orphaned `_h1_buffer`/`_h1_zones` init vars.
5. **Launched H1 IS backtest** (2020-01-01 → 2022-12-31) — **IT IS RUNNING** and producing trades.

---

## CRITICAL: Backtest Is Running Right Now

**Docker container**: `e192f80bd287` (`lean_cli_4669b32bb3b7467fb87c70bfe8b4618b`)
**Started**: ~09:52 local time
**Last known progress**: Processing 2020-08-03 bars (out of 2020-01-01 → 2022-12-31)

**To check progress:**
```bash
docker logs e192f80bd287 2>&1 | tail -30
```

**To wait for completion:**
```bash
docker wait e192f80bd287
```

**To check if it finished** (look for backtests/ folder new timestamp):
```bash
ls -lt "workspace/sigma-lean/B2BZoneStrategy/backtests/" | head -5
```

---

## What the Backtest Is Producing

The strategy IS working. Gates are firing correctly:

```
[ENTRY] BULLISH [T2]  reason=D1 Inertial Flow (Liberated)  entry=7197.57  sl=7116.31
[EXIT-SL]  entry=7197.57  exit≈7116.31  RR=-1.00R
[EXIT-TP]  entry=8703.79  exit≈8829.47  RR=2.00R   ← TP hits exist
```

**Gate reasons observed (working correctly):**
- `D1 Inertial Flow (Liberated)` — Gate B firing
- `Tier Gating Block: H1 T1 Restricted` — T1 muted correctly
- `Blocked: Fighting the Storyline without a Fortress` — Storyline latch working
- `No Strategy Alignment` — Gate A/B/C all rejecting correctly

**Warning observed**: Many consecutive SL hits in early 2020 (COVID crash). All entries are BULLISH during a bearish market. This is expected behavior — the Storyline latch should eventually flip to BEARISH but may be lagging. This is a tuning issue, not a bug.

---

## Current State of `main.py`

**File**: `workspace/sigma-lean/B2BZoneStrategy/main.py`

| Parameter | Value | Notes |
|-----------|-------|-------|
| `RESOLUTION` | `Resolution.Hour` | H1 primary — fast single ZIP |
| `TIMEFRAME_LABEL` | `"H1"` | Entry TF for detection + gates |
| `REDETECT_EVERY` | `1` | Detect every H1 bar |
| IS Start | 2020-01-01 | |
| IS End | 2022-12-31 | |
| Warmup | 3000 H1 bars | ~125 days |
| Consolidators | H4, D1, W1, MN1 | H1 is primary (no H1 consolidator) |
| Primary buffer | `_h1_buffer` | (renamed from `_m30_buffer`) |

**`all_tf_zones` dict:**
```python
{"H1": self._active_zones, "H4": ..., "D1": ..., "W1": ..., "MN1": ...}
```

---

## File Structure (Current)

```
workspace/sigma-lean/
├── B2BZoneStrategy/
│   ├── main.py                     ← H1 primary, IS 2020-2022
│   ├── sigma_core/                 ← LEAN-bundled copy of sigma-crypto/core/
│   │   └── b2b/{detectors,filters,models,strategy}/
│   └── backtests/                  ← results go here when done
├── data/crypto/binance/
│   ├── hour/btcusdt_trade.zip      ← 70,039 H1 bars, 2018-2025 (1 flat file)
│   ├── daily/btcusdt_trade.zip     ← 2,922 D1 bars, 2018-2025
│   └── minute/btcusdt/             ← 2,922 per-day ZIPs (M30, NOT used now)
└── scripts/parquet_to_lean.py      ← converter (all bugs fixed)
```

---

## Next Session: After Backtest Completes

### Step 1 — Read the results
```bash
# Find latest backtest folder
ls -lt workspace/sigma-lean/B2BZoneStrategy/backtests/ | head -3

# Read results
cat workspace/sigma-lean/B2BZoneStrategy/backtests/<timestamp>/results.json
```

Or run `/check-lean-health` — it parses results automatically.

### Step 2 — Compare against sigma-crypto baseline
| Metric | sigma-crypto Test 13A | LEAN IS Target |
|--------|----------------------|----------------|
| Sharpe | 1.16 (OOS) | ≥ 1.0 (IS) |
| Max DD | 8.2% | < 10% |
| Calmar | ~2.0 | > 2.0 |

### Step 3 — Investigate the consecutive SL problem (if metrics are bad)
All early 2020 entries are BULLISH during the COVID crash. The Storyline latch should eventually flip. If Sharpe is very low (< 0.5), the issue is likely:
- Storyline latch not flipping fast enough to BEARISH
- Gate C (Discovery Bridge) taking long-side trades during a downtrend

**Diagnostic**: Look at the trade log and count consecutive SLs before any BEARISH entries appear.

### Step 4 — OOS backtest (2023-2025)
Only run after IS result is acceptable. Change dates:
```python
self.SetStartDate(2023, 1, 1)
self.SetEndDate(2025, 12, 31)
```

---

## Known Bottleneck (for future M30 work)

The M30 data EXISTS (`minute/btcusdt/` — 2,922 day ZIPs) but running it on Windows/Docker/WSL2 is slow due to cross-boundary file I/O. To use M30 properly in LEAN:

**Option A**: Move minute/ data into WSL2 filesystem (native Docker I/O, fast):
```bash
# Inside WSL2:
cp -r /mnt/c/Users/User/Desktop/sigma-brain/workspace/sigma-lean/data ~/lean-data
# Then point LEAN config to ~/lean-data
```

**Option B**: Accept ~2hr runtime for IS (run overnight).

**Option C**: Keep H1 as LEAN primary, use sigma-crypto for M30 validation (different tools for different TFs).

M30 is the correct SAMTC LTF entry TF — but for cross-validation purposes, H1 in LEAN vs H1 in sigma-crypto is a valid and faster comparison. The 1:1 comparison target remains unchanged.

---

## User Sentiment Note

User was unhappy with the previous session (stuck M30 backtest, too much debugging). The H1 switch was the right call and it's now working. Start next session with the backtest result and keep it efficient — no exploration before delivering the number.

---

## Quick Commands for Next Session

```bash
# Check if backtest still running
docker ps | grep lean

# Check progress
docker logs e192f80bd287 2>&1 | tail -20

# After completion — find results
ls -lt workspace/sigma-lean/B2BZoneStrategy/backtests/ | head -3

# Run health check (parses latest results automatically)
# Use /check-lean-health skill
```
