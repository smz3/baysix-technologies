# Handover — June 26, 2026 Evening

## State (FOB v1.15.0 — visuals refactored to ONE zone-primary layer; VISUAL-ONLY, no trade-wiring)
- Pushed (3 commits). Both EAs compile **0 errors** (1 cosmetic MQL5-Market `#property version` warning — `1.15.0` isn't `xxx.yyy`, ignore).
- **Unified layer:** `InpShowSequence` DELETED; `InpShowZones` is the single switch. `RedrawCurrentTF` (the dot-fan) removed entirely. Role-resolution (active-cycle gate, dual-purpose own+parent detect, lifecycle badge) now shared via [ReconstructState + DrawZoneForBreak](mt5/Include/fob_system/fob_visual.mqh) and feeds the zone edge labels — killed the old `curSeq` duplication.
- **Visual model (approved w/ Syafiq):** all text OUTSIDE the band on L1/L2 edges, BRC placement, ALL CAPS. **Parent-primary** — a break that's its own PBO (TF E) *and* a VR/CF for TF E+1 shares ONE band; the band takes the PARENT identity+colour (CF green / VR yellow, VR flips DIR), own PBO demoted to a lowercase secondary fan. PBO-only = all-blue, lifecycle badge rides L2. Dead/invalid zones DROPPED (no band → no draw).
- **Anchoring:** all labels `ANCHOR_LEFT_*` → render RIGHT into the empty ray area (off the candles). Dual secondary trails the primary on the same row via [RightOffset()](mt5/Include/fob_system/fob_visual.mqh) (px↔bar scale, recomputed each redraw → zoom-stable). Glyph est bumped 0.62→0.85 +2-char pad after an overlap report.
- 4 call sites rewired (2 per EA): `DrawZones` now ClearAll's + draws bands+labels; `DrawStructure` layered after.

## Why (decisions — don't re-litigate)
- **Inner-band text rejected** — overlaps + crosses lines on thin zones. ALL text moved outside.
- **Parent-primary** — the parent VR/CF is the *purpose* of the break; the local PBO is just its birth. So band colour/identity follow the parent when present.
- **Two-colour single row = two objects pinned to one origin** — MT5 caps one colour per text object. RightOffset flows the second one right of the first.

## Ruled out (don't re-propose)
- Direction colouring (red sell / green buy) — use ROLE colours only: PBO blue / VR yellow / CF green.
- Inner-zone text; greyed dead zones; the dot-fan / `InpShowSequence`.

## Next
1. **(task 177, P1)** VISUAL-VERIFY v1.15.0 — emitter, Visual Mode, flip TFs. Confirm right-render off candles, dual two-colour row no-overlap, parent-primary colour, PBO-only all-blue+badge, dead zones vanish. (full checklist in task 177)
2. **(task 177 caveat)** If RightOffset still drifts at zoom → switch dual to **meet-at-origin** (primary right via ANCHOR_LEFT, short secondary left via ANCHOR_RIGHT) — zero width-guessing, but secondary sits left of the connector.
3. **(task 179, P1)** After visual signs off: wire trader SL = `zone.l2` (no fallback) + close opposite-thesis on a new opposite PBO. Then task 175 (RR/SL sweep).

## Blockers
- `strategy_log` zone entry STILL not logged (PROPOSED since v1.14.0) — `log_change(component=zone_detection, verdict=CREATED)` once task 177 passes.
- Compile = `metaeditor64.exe` (JustMarkets) direct from Bash: `/compile:<f> /inc:mt5/ /log:<f>.log`, log UTF-16LE. PowerShell route DENIED.
