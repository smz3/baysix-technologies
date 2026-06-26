# Handover — June 26, 2026 Morning4

## State (FOB direction settled = continuation; ATR stripped; TF-pair enum added — next = RR/SL sweep)
- **DIRECTION SETTLED via clean flip test (result_id 15, strategy_log 76).** Added `InpFlipDir` (buy-CF→SHORT) in ATR symmetric mode, ran it: flip confirmed fully ON (opposite-dir 1.000). **Both sides lose; fade (−$1283, WR 41.94%) is WORSE than continuation (result_id 12: −$1112, WR 42.88%).** → direction sign is NOT the lever; loss = spread/stop **cost tax (~$1200)**, ~14× the faint continuation edge (~$171 tilt). The prior session's "fade is the signal" reframe is **FALSIFIED**. Original continuation logic is the correct sign.
- **EA cleaned (v1.12.0, sha e411499):** `InpFlipDir` removed; **ATR fully stripped as a trading/SL mode** (no `InpRMode`/`InpAtrMult`/`FOB_RMODE`). ATR handle kept ONLY as the study-mode MFE/MAE unit (`InpAtrTf`/`InpAtrPeriod` = `[study]`). New **`FOB_TF_PAIR` enum `InpTfPair`** (M5_M1=0…D1_H4=5; `g_setup_tf=InpTfPair+1`) = one-click TF sweep. Compiles 0 err (1 cosmetic Market warning).
- **CURRENT SL (Syafiq's confusion — exact):** SL = the **broken CF swing level** (`e.level`, the swing the CF broke), pushed beyond by `InpSlBufferK × penetration`. At default **`InpSlBufferK=0` the SL sits EXACTLY at that swing level** — NOT the CF candle's low/high. `risk = |entry − SL|`. CF_ZONE *is* implemented — the "zone" = that level ± buffer. RR is set by **`InpRMultTP` alone** (TP = entry ± risk×RR); SlBufferK only widens the stop. So RR=3.0 ≠ needs SlBufferK change — they're independent knobs.
- Syafiq did a naked M15→M5 sanity run (`InpTfPair=1`, CF_ZONE): equity still negative (user quick-test, no ledger logged). Sanity done → now tune RR/SL.
- Deleted stale configs: fob_flip_test.ini, v1.11.0 FLIP preset, v1.8.0 ATR + CFZONE presets.

## Next
1. **(task 175, P1) RR/SL sweep.** Set `InpRMultTP=3.0` first, CF_ZONE, on H1 (`InpTfPair=3`) + M15 (`InpTfPair=1`), dukas real ticks 2016→2024. Then sweep `InpSlBufferK` (0, 0.5, 1.0, 2.0) to widen the stop beyond the swing. Goal: RR/stop combo that flips equity positive. Rank by net $/trade + survival, NOT E[R] ([[er_denominator_illusion]]). Payoff asymmetry is the lever now direction=continuation is confirmed (result_id 15).
2. **(task 171, P1) New/better entry logic** after RR/SL locked — limit-on-pullback/retest into PBO zone (`InpEntryMode = MARKET | LIMIT_PBO`): cheaper fill, lower MAE, stops paying the breakout spread tax.

## Blockers
None. Compile = `powershell.exe -Command Start-Process` of JustMarkets MetaEditor64 (allowlisted, terminal can stay open). Tester run needs JM terminal CLOSED + Syafiq flat (live $50 XAUUSD on it). FTMO/OANDA MT5 still installed — uninstall to kill the wrong-broker trap.
