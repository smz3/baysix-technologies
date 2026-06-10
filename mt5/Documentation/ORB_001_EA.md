# Sigma_ORB_V1 — ORB-001 Standalone EA

**File:** [Experts/Sigma_System/Sigma_ORB_V1.mq5](../Experts/Sigma_System/Sigma_ORB_V1.mq5)
**Status:** compiled (0 errors / 0 warnings via MetaEditor64 CLI), 2026-06-11. Awaiting JM **demo** attach (D1).
**Magic:** 1001 · **Comment:** `ORB001` · **Symbol:** XAUUSD.s

## Why standalone
ORB-001 is shipped as its own EA — **not** a module in the live Sigma B2B EA — so a bug here cannot touch the B2B money-maker. Own magic (1001), own chart, no shared state. Magic 1001 + comment `ORB001` are the keys execution.db's D1 fill adapter reconciles against.

## Frozen live config (research.db `get_live_config('ORB-001')`)
anchor **09:00 UTC** / **N=5 min** opening range / **immediate breakout** / **trail_1R** exit / **Mode-A** min-lot with **5% risk-skip** cap. All are inputs, defaulted to the validated values.

## Logic (per UTC session)
1. **OR build** — over [09:00, 09:05) UTC from M1 bars (bar high/low). `range_w = OR_high − OR_low = 1R`.
2. **Entry** — after 09:05, first breach wins (intra-bar/immediate): `bid ≥ OR_high → long`, `bid ≤ OR_low → short`. One trade per session.
3. **Stop / exit** — initial SL = opposite OR boundary (risk = range_w). **trail_1R**: trailing stop held `range_w` behind the peak favourable price, raised (long) / lowered (short) only.
4. **EOD-flat** — close at 21:00 UTC (swap-free + flat = no overnight cost). No new entries after EOD.
5. **Sizing** — fixed min-lot (0.01). **Skip** the session if `$risk = range_w × 100 × lot` exceeds `InpRiskCapPct%` of equity (Mode-A 5% cap). One decision per session.

## Inputs
| Input | Default | Meaning |
|---|---|---|
| InpMagic | 1001 | order magic |
| InpAnchorHourUTC / MinuteUTC | 9 / 0 | OR anchor (UTC) |
| InpORMinutes | 5 | N (OR length) |
| InpSessionEndHourUTC | 21 | EOD-flat (UTC) |
| InpLot | 0.01 | fixed lot |
| InpRiskCapPct | 5.0 | skip if $risk > this % equity |
| InpUTCOffsetOverrideHours | 999 | 999 = use TimeGMT(); else server→UTC hrs (VPS fallback) |
| InpMaxSpreadPoints | 0 | 0 = off; else skip entry if spread > N points |

## Time base
Anchors are UTC via `TimeGMT()` — correct on a PC with a correct clock/timezone. On a VPS with a skewed clock, set `InpUTCOffsetOverrideHours` to the broker-server→UTC offset (JustMarkets = **+3** in summer/EEST).

## Deploy (DEMO first — never live until D1 passes)
1. In the JM MT5 terminal: **right-click Navigator → Refresh** (it appears under Expert Advisors as *Sigma_ORB_V1*).
2. Open an **XAUUSD.s** chart (any timeframe — the EA is tick-driven).
3. Drag *Sigma_ORB_V1* onto it; enable **Algo Trading**; confirm inputs = defaults.
4. Watch the Experts log for `[ORB-001]` lines: `new session` → `OR set` → `ENTER`/`SKIP` → trail → `CLOSE (EOD)`.

## Toolchain note
Compiled headless from the repo via `MetaEditor64.exe /compile:... /inc:... /log:...`. The terminal's old `Experts/Sigma_System` symlink (→ `sigma-brain/.../b2b-mt5`) is **dangling** — the live B2B EA runs from its existing `.ex5`, so trading is unaffected, but that link should be repointed at some stage. ORB lives at top-level `Experts/` to avoid it.

## Next (D1)
Forward parity proof + MT5 fill adapter (HistoryDeal* → execution.db) — backlog task 35. This is where live signals/fills are reconciled vs the Python recompute on the **same** JM live feed.
