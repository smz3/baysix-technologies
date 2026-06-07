# Handover — June 3, 2026 Afternoon

## State
B2B detection engine **recovered** from git (`a423747`, pre-scorched-earth) into [b2b/sigma_core/](b2b/sigma_core/) as a proper package; dead flat `b2b/code/` retired. Engine imports + runs. We **pivoted from plotly eyeballing to objective parity** — verifying Python detection against the live MQL5 EA's own exported zones, using a working MT5↔Python bridge. Parity numbers exist but are **NOT trustworthy yet** (CSV parse bug, see Findings #5).

## Critical Findings
1. **Detection LOGIC is faithful to the EA** (verified by static read of the `.mqh`): swings = 3-bar strict close-extrema (`InpSwingWindow=3` confirmed), zone geometry (P1–P5 / P4 / L1=P2 / L2=max·min(P1,P3) / 50%), + ported the two missing passes (PASS2 freshest-per-P5, PASS3 IsSwingUsedInZones dedup). **17 unit tests green** ([b2b/tests/test_detectors.py](b2b/tests/test_detectors.py)).
2. **Invalidation rule confirmed Python==MQL5**: close > max(L1,L2) (sell) / < min(L1,L2) (buy), zone's own TF, first close wins. Touch tracking (T1/T2/T3) needs high/low.
3. **MT5 bridge works** ([b2b/bridge/pull_bars.py](b2b/bridge/pull_bars.py)). `MetaTrader5` pkg, symbol = **`XAUUSD.s`**. Pulled broker OHLC D1/H4/H1 → `data/parquet/bars/mt5/` (2011→2026, **weekday-only**).
4. **EA exports zones to CSV** (ground truth): `C:/Users/User/AppData/Roaming/MetaQuotes/Terminal/Common/Files/SIGMA_Quant/Zones/QUANT_ZONES_*.csv` — CREATED/TOUCHED/SURVIVED/BULLDOZED, 40 cols, full history.
5. **⚠️ PARITY NUMBERS UNRELIABLE — CSV parse bug.** Diff showed 427/971 D1 "exact match", but ~half the QUANT_ZONES files have **NO header row** (row 0 is data like `CREATED,...`), so `pd.concat` misaligned columns → garbage prices (gaps up to 118k). Re-parse with explicit header BEFORE trusting any %.
6. Weekend bars: EA's historical D1 had Sat/Sun bars; current pull is weekday-only → a *partial* cause, but moot until #5 fixed.
7. Dukascopy resampler ([b2b/backtest/resample_bars.py](b2b/backtest/resample_bars.py)) = deep-history source (GMT+3, bid). MT5 bridge = parity source.

## Done / committed
- Commit `928d130` (pushed): recovery + port + 17 tests.
- Commit `c811bee` (**LOCAL ONLY, not pushed** — needs approval): bridge + diff harness + resampler.
- Uncommitted: [b2b/backtest/render_zones.py](b2b/backtest/render_zones.py) — half-state plotly, superseded by MT5-as-truth. Leave it.

## Next
1. **Fix CSV parsing in [b2b/bridge/diff_zones.py](b2b/bridge/diff_zones.py)**: detect header vs headerless files; apply the 40-col names from [QuantLogger.mqh:538](mt5/Include/Sigma_System/V5.0/Data/QuantLogger.mqh#L538) (`event_type,zone_id,tf,direction,l1_price,l2_price,fifty_percent,first_barrier_price,first_barrier_time,...,dataset_type`) with `header=None`, drop embedded header rows. Re-run → get the TRUE D1 match rate.
2. Re-assess parity on clean data. If a real gap remains, run **EA fresh in Strategy Tester** on current weekday-only bars → fresh QUANT_ZONES → diff on identical input (the only way to guarantee matched bars).
3. Push `c811bee` once approved.

## Blockers
Parity verdict blocked until CSV header parsing is fixed (#5). Push of `c811bee` awaits user approval.
