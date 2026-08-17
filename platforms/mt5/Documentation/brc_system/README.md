# BRC System (MT5)

Break–Retest–Continuation on XAUUSD. Two EAs, shared detection includes.

## EAs
- **`brc_baysix.mq5`** (emitter) — read-only chronological oracle. Detects zones across 8 TFs
  on one M5 run, writes a UTF-8 lifecycle CSV → ingested to `tester_zones`. No orders. Run on M5,
  "Open prices only". Keep pristine (needed pure for OOS re-emits).
- **`brc_trader.mq5`** (trader) — the strategy. Reuses the emitter's detection on the **chart TF**
  (run on H1 for IS-01), trades via swappable modules. Run "Open prices only".

## Modules (the control surface — iterate by flipping inputs, not editing code)
| Module | Inputs | IS-01 default |
|---|---|---|
| `brc_entry.mqh` | `InpEntryTouch` (L1/MID/L2), `InpEntrySide` (CONTINUATION/FADE) | L1, CONTINUATION |
| `brc_exit.mqh` | `InpExitMode` (TIME/TIME_TP), `InpMaxHoldBars`, `InpTpMult` | TIME, 6, 0.0 |
| `brc_sizing.mqh` | `InpSizeMode` (FIXED_LOT/FIXED_FRAC), `InpFixedLot`, `InpRiskPct` | FIXED_LOT, 0.01 |

## Build (headless)
1. `python core/infra/gen_brc_version.py`   (stamps git sha → `brc_version.mqh`)
2. MetaEditor64 `/compile:...brc_trader.mq5 /inc:<repo>/mt5` — `/inc` is the MQL5 root (has `Include/`), NOT `mt5/Include`.
3. Compile log is UTF-16.

## Run (IS-01)
- Strategy Tester → `brc_trader` → XAUUSD, **H1**, model **Open prices only**, 2016-01-01 → 2024-06-30, deposit 50.
- Load preset `presets/brc_system/brc_trader-v1.0.0-IS01.set`.
- The MT5 report (.xlsx → `mt5/strategy_tester_xlsx/`) IS the trusted number. Query-layer math is never a verdict.

## Atom (IS-01)
Enter at the first pullback to the near edge (L1) in the break direction; stop where the zone
invalidates (L2); close after 6 H1 bars; no take-profit; one position at a time; 0.01 lot.
