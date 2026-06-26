# Handover — June 26, 2026 Evening2

## State (FOB visual layer v1.16.2 — verified live by Syafiq; VISUAL-ONLY, no trade-wiring)
- Both EAs compile **0 errors** (1 cosmetic MQL5-Market version warning — ignore). Pushed (5 commits this session). HEAD `869f96f` is the strategy_log probe only; latest code commit is v1.16.2.
- **Secondary label restack (v1.15.1/1.15.2):** horizontal RightOffset DELETED (it guessed text *width* → drifted/overlapped at zoom). Replaced by [VertOffset](mt5/Include/fob_system/fob_visual.mqh) — the blue own-PBO secondary STACKS one row OUTSIDE L1 (above for bull top-edge, below for bear), same x, so it can't collide horizontally. Two objects = two colours kept (MT5 caps one colour/object). Both PBO bits (id + lifecycle badge) share ONE blue row; L2 has no secondary. Now ALL CAPS: `PBO D1 #20 · PENDING H4 CF`.
- **Live intrabar T-touch (v1.16.0, BRC parity):** FOB stamped T1/T2/T3 from CLOSED bars only → `[Tn]` flipped at bar close. Ported BRC's forming-bar pass: [FobLiveTouch](mt5/Include/fob_system/fob_lifecycle.mqh) (touch-only, **invalidation stays close-only**) + [CFobVisual::LiveTouchForming](mt5/Include/fob_system/fob_visual.mqh). Runs each live tick, tester-guarded OFF (per-tick quadratic) → **zero ledger impact**.
- **Twitch fix (v1.16.1):** v1.16.0 repainted (ClearAll+redraw) every tick → flicker. [StateSignature](mt5/Include/fob_system/fob_visual.mqh) (FNV-1a hash of touch ladder + alive/valid + count) gates the redraw — repaint ONLY on `np>0` OR signature change (trader also folds in live-cycle count). Stamping still runs each tick; only the draw is gated.
- **CF label (v1.16.2):** `CF1 W1 #14 SELL` — CF ordinal rides "CF", `#` is plain seq (was `CF W1 #14.1 SELL`).

## Why (don't re-litigate)
- Vertical stack chosen over horizontal: a one-line vertical gap is far more robust than guessing a 40-char width; left-anchored rows never garble.
- Repaint-on-change (not per-tick) = BRC's actual model — it surgically updates a zone only when its touch advances.

## Next
1. **(task 179, P1)** Wire trader SL = `zone.l2` (no fallback) + close opposite-thesis on a new opposite PBO. File: [fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5).
2. **(task 175, P1)** FOB RR/SL sweep: RMultTP=3.0 + SlBufferK variants (after 179).
3. **(task 171, P1)** FOB retest entry: limit-on-pullback into PBO zone vs market-on-CF.

## Blockers
- None. (Long-standing "log zone_detection CREATED to strategy_log" PROPOSED item CLOSED as not-applicable: the visual layer is pure infra with zero ledger impact — `zone_detection` isn't even a valid strategy_log component. No lineage row needed.)
