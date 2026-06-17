# BRC Zone-Emitter EA — Design Spec

**Idea:** BRC-001 · **Gate:** 3 (edge test, falsified 3/2 — reframed, NOT killed)
**Decision log:** human call_id 77 (MT5-first emitter), call_id 78 (Layer separation)
**Tasks:** 118 (build) · 119 (ingest) · 120 (Python funnel inference)
**Authored:** 2026-06-17 · fresh build, old Sigma B2B stack = read-only reference only.

---

## 0. Why this exists (the three layers)

- **L1 — Fidelity:** does the detector fire per the 5-point spec? MT5 = the chronological oracle that settles this. Event-driven `OnBar` structurally kills the vectorized argmax-by-position look-ahead that manufactured the earlier "edge."
- **L2 — Does BRC behave? (THIS build's deliverable):** of zones that confirm per spec, does price come back, retest, and **continue** rather than die? Measured as a lifecycle **funnel of base rates**, per TF M5..MN1, + an unconditional same-direction random-bar **continuation control**. No strategy, no money, no beta.
- **L3 — Edge vs trend-beta:** only after a real tradeable rule exists. The trend confound lives HERE, not in L2.

The EA's only job: **emit a trustworthy, chronological zone-lifecycle ledger across all 9 TFs.** All inference is downstream in Python on the CSV.

---

## 1. What the emitter implements: PATH B (the owned, locked spec)

There are two candidate 5-pointer detectors. They produce **different** zones:

| | Old live `B2BDetector.mqh` | **Path B (zones.py — LOCKED)** |
|---|---|---|
| Confirmation | swing-scan + plain `close < P5` | consumes the **rawbreakout** stream (2 same-dir breaks) |
| P3 gate | none (absorbs P3>P1 via L2=extreme) | **P3 < P1** required (SELL); reject otherwise |
| Accuracy gates | partial | freshness + gap-validation + one-zone-per-P5 dedup |

The emitter implements **Path B** (strategy_log #48, human call_id 76). The old EA's 5-pointer logic is NOT replicated — only its two upstream *primitives* (swing + rawbreakout), which the Python faithfully re-ported, are reused as logic reference.

### Detection chain (3 stages — port from owned Python, self-contained, no Sigma includes)

1. **Swings** — close-based pivot engine, `swing_window = 3` (live EA `InpSwingWindow=3`); a swing confirms at `radius = window//2` bars after its pivot. Ref: `detectors.detect_swings` / `SwingPointDetector.mqh`.
2. **Raw breakouts** — bull: `close > swing HIGH`; bear: `close < swing LOW`. Per-bar **two-pass with shared L2** (earliest broken swing computes L2 once, shares to all same-bar breaks); stateful `has_been_broken` (a swing breaks once); confirmation gate; `max_age` filter. Ref: `rawbreakout.py` / `RawBreakoutDetector.mqh`.
3. **5-pointer pairing (Path B)** — SELL (BUY = mirror):
   - `P1` = swing HIGH (L2 origin) · `P2` = first LOW after P1 (= **L1 entry**) · `P3` = first HIGH after P2 **with P3 < P1** (else reject) · `P5` = closest LOW older than P1 with `price < P2` (the 2nd barrier).
   - **Confirmation:** `P4` = the bar whose break event broke `P5` (the 2nd break). No P5 break ⇒ not confirmed ⇒ no zone.
   - `break_kind` = `same_bar` if the P2 break and P5 break are the same bar, else `sequential` (H_alt-2 input).
   - **Levels:** `L1 = P2.price`; `L2 = max(P1,P3)` SELL / `min(P1,P3)` BUY (= P1 under the restored gate); `mid = (L1+L2)/2`.
   - **Accuracy gates (reject zone if any fail):** (a) **freshness** — no swing strictly between P3 and P4; (b) **gap-validation** — no bar in `(P3, P4]` closes beyond L2; (c) **one-zone-per-P5 dedup** — keep the freshest P1 per P5 barrier.

### Lifecycle (per confirmed zone — the new tracking the EA adds)

- **Retest ladder** (wick-based, intrabar touch): `T1=L1`, `T2=mid`, `T3=L2`. SELL touched when `bar.high >= level`; BUY when `bar.low <= level`. Record each level's first-touch bar in the lived span `(P4, invalidation]`.
- **Invalidation** (close-only): first bar that **closes** beyond L2 (a wick poke of L2 = a T3 touch, zone stays alive).
- **Continuation:** from the L1 retest entry — `MFE_R` / `MAE_R` in `R = |L1−L2|`, `realized_R` of an unmanaged hold (stop L2, no TP, exit on invalidation or data-end), and `continued` = did a bar close ≥ +1R in break direction before invalidation.

---

## 2. Execution model (multi-TF, one run)

- **One EA on the M5 chart.** On each TF's new-bar event (M5,M15,M30,H1,H4,D1,W1,MN1 — 8 TFs; "all 9" incl. M5 base), pull that TF's closed bars via `CopyRates(symbol, PERIOD_X, …)` and advance that TF's detection state.
- **Incremental, event-driven** (not full rescan per bar): maintain a per-TF swing buffer + open-zone list; on each TF bar close, detect new swings/breaks, try to confirm new zones, and update every alive zone's retest/invalidation state. This is how the live EA runs (CircularBuffer) and keeps a 10-yr M5 run tractable.
- **Tester model: "Open prices only."** Detection + invalidation are **close-only**, so each bar's final OHLC is known at its close — open-prices model is *exact* here and far faster. (Retest wicks use bar high/low, also final at bar close.) ⚠️ confirm this holds before the long run.
- **Aligned timestamps:** because all TFs are detected in one run on one clock, a low-TF zone's outcome can later be conditioned on the high-TF zone state active at the same instant (the russian-doll cross-reference, Python L2 step).

---

## 3. Output schema — `tester_zones` (one row per confirmed zone per TF)

UTF-8, header row, comma-delimited. **NOT** the old UTF-16 / headerless QUANT_ZONES format (that broke ingestion — reference_mt5_bridge).

```
zone_id            int     monotonic, unique within the run
tf                 str     M5|M15|M30|H1|H4|D1|W1|MN1
direction          str     SELL|BUY
p1_time,p1_price            L2 origin swing
p2_time,p2_price            L1 entry swing (1st-break target)
p3_time,p3_price            context-gate swing (P3<P1)
p4_time,p4_price            confirmation bar (broke P5) — close
p5_time,p5_price            2nd barrier swing
l1,l2,mid          float   L1=P2 · L2=extreme(P1,P3) · mid
break_kind         str     same_bar|sequential
t1_time,t2_time,t3_time     first wick touch of L1/mid/L2 (blank if never)
confirm_time              = p4_time (redundant, convenience)
invalidation_time         blank if alive at data-end
alive_at_end       int     0|1
continued          int     0|1  (closed >= +1R before invalidation)
mfe_r,mae_r        float   from L1 retest entry, R=|L1-L2|
realized_r         float   unmanaged hold to invalidation/data-end
bars_alive         int     P4 -> death/data-end
```

Path: `<MT5>/Common/Files/BRC/brc_zones_<symbol>_<runid>.csv`.

---

## 4. Module layout (`brc_system` namespace — decoupled from Sigma)

```
mt5/Experts/brc_system/BRC_Emitter.mq5        ← EA shell: OnInit/OnTick new-bar gate, per-TF loop, CSV writer
mt5/Include/brc_system/BrcSwings.mqh          ← close-based swing pivots (self-contained)
mt5/Include/brc_system/BrcBreakouts.mqh       ← two-pass shared-L2 rawbreakout primitive
mt5/Include/brc_system/BrcZones.mqh           ← Path-B 5-pointer pairing + accuracy gates
mt5/Include/brc_system/BrcLifecycle.mqh       ← retest ladder + invalidation + continuation
mt5/Include/brc_system/BrcCsv.mqh             ← UTF-8 lifecycle-row writer
```

Self-contained: no `#include` into the Sigma_System tree. Compile headless via MetaEditor64 CLI (orb_ea_deployment_conventions).

---

## 5. Validation (L1 fidelity, before the long run)

1. Hand-check the EA fires per spec on one known D1 window.
2. **Fidelity-diff** EA-D1 zones vs Python `detect_zones('D1')` — quantifies how much look-ahead the vectorized Python injected. Diagnostic only; MT5 is the oracle.

---

## 6. Out of scope (deferred, do NOT build now)

- Strategy / sizing / position management (L3).
- Trend-beta matched-random baseline (L3 — Python, only after L2 passes).
- Full swing-reuse exclusivity across zones (EA PASS 3) — Python also defers it.
