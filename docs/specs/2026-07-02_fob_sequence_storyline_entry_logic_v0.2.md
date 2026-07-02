# FOB Sequence-Storyline Entry Logic (Spec v0.2 — LOGIC ONLY, STATE-MACHINE REFRAME)

**Date:** 2026-07-02
**Status:** PROPOSED — logic locked for review; NOT built, NOT measured. Cost/measurement deliberately excluded (discovery is cost-free; logic must be correct before any test).
**Supersedes:** [v0.1](2026-07-01_fob_sequence_storyline_entry_logic.md) — replaces its structural-containment recursion (§2/§3/§7) with a live-state-machine model derived from Syafiq walking through a real 2026-07-02 XAUUSD entry. v0.1 is retained for lineage; **v0.2 governs.**
**Cross-refs:** [awareness/conditioner spec v3](2026-07-01_fob_awareness_conditioner_spec.md) · [CMP storyline model](2026-06-27_fob_cmp_storyline_model.md) · [FOB manual dissection](../../research/papers/fob/FOB_breakout_system.dissect.md).

---

## 0. What v0.2 changes (read this first for review)

- **"Too big" is a PIP threshold, not structural containment.** v0.1 §2/§7 banned pips ("No pips, no ratio, no ATR") in favour of a fractal containment test. **Wrong.** Syafiq's actual rule: breakaway candle from L1 **< 20 pips / 200 points → enter market; > that → wait for pullback into the CF L1–L2 zone.** The containment machinery (and its 13-question tail) is deleted.
- **Leaf-finding = live-state chain walk, not a containment fit test.** Walk the control chain top-down; stop at the deepest TF whose **CF is LIVE**; skip any level that is only **pending**. (Resolves v0.1 Q8: live CF = actionable, pending = not.)
- **Two missing layers added: LOCATION and HORIZON.** Before picking an execution TF, the trader reads *where CMP sits vs major HTF structure* (at a wall?) and chooses *swing vs scalp*. v0.1 had neither.
- **Task 214 resolved (gate vs conditioner):** they operate at different layers. **HTF stack = conditioner** (bias / location / horizon); **execution TF = the gate** (the trigger). No conflict once layered.
- **Direction is set by the execution-TF live cycle, NOT the HTF bias.** In the worked example HTF bias was BEARISH but the trade was a BUY (the intraday pullback leg). HTF bias picked the *horizon and the read*, not the side.
- **Framing:** this is a **state machine**, not a recursion algorithm. Its product is a **context-keeper + patience-enforcer** — it holds the full storyline every tick (Syafiq's brain drops it mid-trade) and refuses to fire until the trigger is true (Syafiq's impatience is the leak). We are encoding a known discretionary edge without its two human leaks, not searching for a new edge.

---

## 1. Core definition

- **Storyline = a live readout of what every timeframe's setup is currently doing.** That is all it is. For each TF on the control chain **MN1 → W1 → D1 → H4 → H1 → M30 → M15 → M5 → M1**, the machine holds a state: `{ direction, phase, cf_idx, vr_fresh, zone levels }`.
- **A TF's direction = the direction of its live cycle one TF below** (awareness spec dec 5, bottom-up). Read top-down for context.
- **Per-TF phase vocabulary** (from the awareness spec, locked):
  - `PBO` — primary breakout printed, cycle born.
  - `pending <lower> VR` — PBO done, waiting on the one-TF-below VR. **Not yet actionable.**
  - `VR` — first opposite break one TF below fired; zone born; sets which TF you trade.
  - `live CF (cf_idx = n)` — confirmed continuation live. **Actionable.** `cf_idx` = maturity/strength.

---

## 2. The five layers (the actual process)

**Layer 0 — BIAS (top-down HTF readout).**
Walk MN1 → W1 → D1, reading each TF's live state. Output = directional bias + maturity. *(Worked ex: MN1 bull 5 CFs; W1 PBO sell w/ live D1 CF1 → BEARISH.)* This is **conditioner**, locked before any entry thought.

**Layer 1 — LOCATION ("am I at a wall?").**
Where is CMP vs major HTF zones/levels? At a wall → swing is dangerous **both ways** (sell into the level = bounce; buy = no structure yet). *(Worked ex: CMP at W1 Nov-2025 levels.)* → conditioner.

**Layer 2 — HORIZON (swing vs scalp).**
Chosen *from* location, not fixed. Wall / unfavourable → **intraday/scalp**; open space + clean stack → **swing**. This picks *what kind of trade the market is offering*, not the side. → conditioner.

**Layer 3 — EXECUTION TF (the live-state chain walk = "leaf").**
Starting from the horizon's top TF, walk **down** the control chain reading phases; **stop at the deepest TF with a `live CF`**, skipping any `pending` level. Drop one TF below it to execute. *(Worked ex, intraday: H4 breakout-buy `pending H1 VR` → H1 fresh PBO buy `pending M30 VR` → M30 `pending M15 VR` = SKIP → M15 `live CF1` = STOP. Execute on M15 + M5.)*
- **Direction of the trade = the direction of this execution cycle**, even if counter to Layer-0 bias.

**Layer 4 — TRIGGER (the click).** See §3.

---

## 3. The trigger (execution / leaf TF)

1. **Price pulls back into the leaf's VR/CF zone → WAIT ("chill").** *Never enter while price is sitting inside the VR/retrace zone.* This is the patience the machine enforces.
2. **Resumption + FRESH CF:** enter only when price turns back in the trade direction and a **fresh CF fires** — either (a) price breaks back out of the VR zone and a new CF prints, or (b) price touches the PBO zone and a fresh CF prints there. A stale CF that price has since fallen back through does **not** count.
3. **Breakaway candle from L1 decides the execution mechanic:**
   - **≤ 20 pips / 200 points → ENTER AT MARKET** (small push-off, chasing is fine).
   - **> 20 pips / 200 points → LIMIT ON PULLBACK** into the CF L1–L2 zone (too extended to chase; wait for the retrace).

**Risk is a depth knob, not a rule:** enter on the leaf CF + one-TF-down confirm = *medium risk*; wait for a full deeper cycle inside the zone = *lower risk, tighter entry*. (Worked ex: M15-CF + M5 = medium; full M5 cycle = lower.)

---

## 4. Where the numbers live (only two knobs, both trader-layer)

- **Breakaway threshold** — 20 pips / 200 points (chase vs limit-on-pullback). **Open: fixed vs TF-scaled — see §6.**
- **Leaf depth** — how deep the chain walk is allowed to go (risk tier).

Everything else (bias, location, horizon, phase, direction, fresh-CF) is **read from state**, not parameterised.

---

## 5. v0.1 open questions — disposition

- **Q1 (controlling zone by type):** resolved — zone is read from the live cycle's own state; type is not chosen upfront (no circularity).
- **Q2 (containment window):** **moot** — no containment test in v0.2.
- **Q7 (chain vs rejected alignment gate):** resolved — HTF is **conditioner**, not a directional gate; the chain walk reads *phase state*, not full-stack directional alignment. Distinct from result_id 18/19 by construction (awareness dec 5 independence guard preserved).
- **Q8 (child confirmed?):** resolved — **live CF = actionable; pending = skip.**
- **Q9 Setaman / Q10 counter-scalp / Q5 multi-CF:** deferred — Layer-3 walk already produces "skip CF1 / take CF2" naturally (a stale CF fails the fresh-CF trigger); revisit only if measurement shows a gap.
- **Q11 (RR floor) / Q12 (barrier):** RR floor = trader knob; barrier detector = the Layer-1 LOCATION gap (§6).
- **Q13 (layering):** management, ties to task 168; unchanged.

---

## 6. Genuinely open (before build)

- **Breakaway threshold scaling.** Is 20 pips / 200 pts a **fixed constant**, or **"small relative to *this* execution TF"**? Fixed 20 is right for M5 but tiny for H1 — matters if scalp TF varies. **Awaiting Syafiq.**
- **LOCATION detector (Layer 1).** "At a major HTF wall" has no detector today (old Q12). Needs a barrier/zone-proximity read off HTF structure. Architectural.
- **Trader ingest window.** Full walk needs the trader to ingest the whole band below the setup TF (setup↓M5); today it ingests only `{setup_tf−1, setup_tf}` ([fob_trader.mq5:107-109](../../mt5/Experts/fob_system/fob_trader.mq5#L107-L109)). Emitter already classifies all 9 TFs, so data exists — only the trader ingest is the gap.

---

## 7. Build priority (when we build)

1. **Storyline state display first** — the emitter maintains + draws every TF's live phase/direction so Syafiq can confirm the machine thinks what he thinks. Get this right and the entry is almost trivial.
2. Layer-3 chain walk (live-CF leaf) on top of the state.
3. Layer-4 trigger (fresh-CF + breakaway mechanic).
4. Layers 1–2 (location + horizon) — need the barrier detector; can start as manual/awareness overlay.
