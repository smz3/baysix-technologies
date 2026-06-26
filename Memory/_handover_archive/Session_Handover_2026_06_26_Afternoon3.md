# Handover — June 26, 2026 Afternoon3

## State (FOB v1.14.2 — zone visuals now mirror BRC; VISUAL-ONLY, still no trade-wiring)
- Shipped `c36193c` (pushed). Both EAs compile **0 errors** (1 pre-existing cosmetic MQL5-Market version warning on the `.mq5` `#property version`).
- **Unified dot+zone annotation:** the sequence dot now carries the zone's text — lowercase role grammar + retest tag, e.g. `pbo w1 #16 sell · live d1 cf1 [t0]`. [DrawZones](mt5/Include/fob_system/fob_visual.mqh#L405) draws **geometry only** (L1/L2 dashed + mid dotted + left vertical connector), NO text, NO prices.
- **`[Tn]` on EVERY role** (PBO+VR+CF) — appended to both fanned labels in [RedrawCurrentTF](mt5/Include/fob_system/fob_visual.mqh). Per-sequence touch tracking, for later entry-strategy data (Syafiq).
- **New [UpdateZoneLifecycles](mt5/Include/fob_system/fob_visual.mqh#L380)** stamps T1/T2/T3 + alive (stateless, from chart-TF OHLC) BEFORE redraw; [FobReplayZoneLife](mt5/Include/fob_system/fob_lifecycle.mqh) now takes `(FobZone&, dir, l1, brk, bars…)` so the SAME stamped zone feeds label + geometry. Wired at all 4 call sites (2 per EA).
- **Dead zones DROPPED** (not greyed); **dual-purpose** break = ONE shared band (label-less stem → idempotent).
- Toggles: text=`InpShowSequence`, geometry=`InpShowZones`, P1/P3=`InpShowPoints`, retests=`InpShowRetests`.

## Why (decisions this session — rationale, so they aren't re-litigated)
- **Fold zone text into the sequence dot** — the dot sits at the exact L1 origin; a separate zone label there would duplicate/collide. One text source → can't drift.
- **One band for dual-purpose** — a break's PBO event and its VR/CF event share *byte-identical* geometry (same `FobComputeBreakZone` call), so two bands = same lines twice. Reused the existing dual-dot fan-out.
- **`[Tn]` on all roles, not just PBO** — Syafiq needs per-sequence touch data for entry-strategy research later.

## Ruled out (don't re-propose)
- BRC-style separate `L1/L2` text labels carrying price — removed; redundant with the price axis, trader reads `zone.l2` from the struct not the label.
- Greyed/frozen dead zones — explicitly deleted; live chart shows live bands only.

## Next
1. **(task 177, P1)** VISUAL-VERIFY v1.14.2 — emitter, Visual Mode, M5, flip TFs. Confirm dot `[Tn]` labels, dual-purpose two-labels/one-band, T-dots on right bars, dead zones vanish, bands ray right. (full checklist in task 177 detail)
2. **(task 180, P1)** Harden /handover protocol — add `## Why` / `## Ruled-out` / `## Live threads` to [handover.md](.claude/commands/handover.md) (this file pilots the format); note: promote durable items to memory/strategy_log so handover stays the ephemeral narrative bridge.
3. **(task 179, P1)** After visual signs off: wire trader SL = `zone.l2` (no fallback) + close opposite-thesis positions on a new opposite PBO on `g_setup_tf`. Then run task 175 (RR/SL sweep).

## Blockers
- `strategy_log` zone entry STILL not logged (PROPOSED since v1.14.0) — log `log_change(component=zone_detection, verdict=CREATED)` once task 177 visual-verify passes.
- Compile = `metaeditor64.exe` direct from Bash (`/compile /inc:mt5/`, log UTF-16LE); PowerShell route DENIED. `/handover` filename script is gap-blind (reused archived `Afternoon` slot) — this file hand-named Afternoon3.
