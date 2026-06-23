# Handover — June 23, 2026 Morning2

## State
- **BRC-001 G2 — IS-01 trader now produces a TRUSTED result, and it has NO edge.** First honest baseline (result_id 2): net **−$0.33/trade**, ~1448 trades, full 8.5yr IS, **no ruin at $10k**. 903 SL (~62%), 488 limits expired un-retested. Base/symmetric continuation = bleeds ~spread drag. (clean sha `6d9dd38`, MT5 tester arbiter.)
- **Bug found + fixed this session (committed `6d9dd38`, BRC_VERSION 1.1.0):** the morning's "3 trades / 8.5yr" was a **single-slot starvation** — one GTC limit at L1 rested for years (1.2% of H1 zones never retest *and* never invalidate) while `TryArm` armed **oldest-first**. Fix in [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5): arm **freshest** zone + **72h-since-P4 T1-limit expiry** (`ORDER_TIME_SPECIFIED`, new input `InpRetestExpiryHrs=72`). Limit-at-L1 untouched (it IS the faithful BRC retest entry — confirmed correct, market-fill rejected). strategy_log ADOPTED, cites result_id 2.
- **72h chosen from data**, not guessed: emitted P4→T1 lag over 8.5yr H1 primary zones — 98.8% retest (median 4h, within 24h=78%, 72h=86%); only **1.2% never retest** (= the starvers). Exploratory screen on trusted EA-emitted `tester_zones` (not a gate verdict).
- **Preset:** [brc_trader-v1.1.0-IS01.set](../mt5/presets/brc_system/brc_trader-v1.1.0-IS01.set) (deployed to E7DB terminal). **DELETED** old `brc_trader-v1.0.0-IS01.set` (lacked expiry param).
- **Open methodology debate (unresolved):** Syafiq wants tick/every-tick modelling; I argued limit-at-L1 already fills exactly on bar-OHLC, ticks only add intrabar path + real spread, and full-tick kills the fast sweep. Leaning **1-min OHLC for iteration, real-tick as final pre-live gate**. NOT decided.

## Next
1. **Task 134 (P1):** GET Syafiq's one-liner on the **logic error he eyeballed** in brc_trader.mq5 → fix it, re-run IS-01, compare to result_id 2. Base continuation is ONE falsified framing (not a kill — needs ≥2).
2. **Reframe program vs baseline (result_id 2):** queued #133 exit-robustness / #132 entry-depth (L1→mid→L2) / #131 fade. Each frozen-then-OOS.
3. **Settle the modelling debate** (1-min OHLC vs tick) before trusting variant deltas.
4. **Task 135 (P2):** fix the **headless tester CLI** — `terminal64.exe /config:`[brc_trader_IS01.ini](../mt5/tester/brc_trader_IS01.ini) opens but never runs the test (GUI works ~14s). Terminal must be CLOSED first.

## Blockers
- None hard. OOS #126 still blocked until an IS config is FROZEN — and we won't freeze IS-01 (no edge). Freeze comes from a variant that beats baseline.
