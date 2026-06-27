# FOB — The CMP Storyline Model

**Date:** 2026-06-27 · **Status:** Concept locked (design intent, pre-implementation) · **Idea:** FOB-001
**Supersedes the implicit framing** that FOB entry is a probabilistic win-rate filter. It is not. This doc pins what FOB *is*.

---

## 1. Core thesis — FOB is reaction modeling, not prediction

- **CMP = Current Market Price.** FOB acts on what the market **has already printed**, never on a probability of what it *might* do.
- Every FOB event (PBO / VR / CF, with zone bounds L1/L2) is a **tagged fact that already happened**. We do not forecast the next bar; we **react** to a confirmed sequence.
- Consequence for research: the goal is **not** "raise the probability of being right." It is "**read the storyline the market has written, and choose where in it to act.**" Win-rate is an *output* of trading the right cycle with the right context — not the design target.

> If a test treats FOB as "find the feature that lifts hit-rate," it has mis-specified the system. FOB succeeds by **reading structure**, not by estimating odds.

---

## 2. The storyline — a cycle within a cycle within a cycle

- Markets unfold as **nested cycles**: W1 contains D1 contains H4 contains H1 contains M30 contains M5…
- Each confirmed breakout (CF) on each TF is **a sentence in a story.** Because we have **genuinely tagged every PBO/VR/CF on every TF**, at any instant we know **the storyline so far**.
- A trade is not "a signal." It is **a position within a storyline** — e.g. *"W1 is selling, D1 just confirmed the sell, H4 is pulling back into a VR, H1 just gave a 1st CF down."* That whole sentence is the setup.

**Example (the one we discussed):**
> Gold CMP is a **W1 sell** with a **live D1 CF1**. → Bias is **SELL**.
> Do we sell all the way? **Maybe.** *Why maybe* — because the decision needs **context**: what are D1 → H4 → H1 doing *right now*?
> The real questions then become:
> 1. **Which TF do we want to trade?**
> 2. **Which TF setup do we want to trade?**
> 3. **Which cycle do we want to trade?**

---

## 3. Bias hierarchy — higher TF = context, lower TF = trigger

- **Higher TFs set BIAS and CONTEXT.** W1 sell → macro sell lean. D1 CF → confirms direction. H4 / H1 → refine *where in the move we are*.
- **Lower TFs are the EXECUTION TRIGGER** — the cycle you actually pull the trigger on, for a precise entry.
- "Making FOB feel alive" = giving it **awareness of which cycle is currently *controlling* the storyline** — i.e. which TF's bias is the dominant one the lower TFs must obey.

---

## 4. The simple operating mode (what we build first)

To avoid drowning in the full nested machine, **pick one execution TF** and read the cycle directly below it for precision:

> **H4 setup mode (worked example):**
> 1. Wait for the **H4 VR → CF** to complete (the setup confirms on H4).
> 2. **Do not enter on the raw H4 CF.** Drop to a lower TF and wait for the **first LTF CF** to print, aligned with the H4 bias, for a **more precise entry**. The LTF is **whichever lower TF gives a CF first** — M5 is only an example; it could be M15, M30, etc. (per the FOB manual: on an HTF CF, watch the LTFs and trade the first one that confirms).
> 3. The H4 CF is the *context*; the first LTF CF is the *trigger*.

> **CAVEAT — risk/target stay HTF-anchored (Syafiq, 2026-06-27).** When an LTF is used to *trigger* an HTF CF, the **TP uses HTF logic** (the HTF target) and the **SL sits at the HTF CF zone** — NOT the LTF's own TP/SL. The LTF only sharpens *entry timing/price*; it does **not** shrink the trade to an LTF-sized target/stop. This preserves the HTF payoff structure (where the continuation magnitude lives) while the LTF buys a tighter, better-located entry → mechanically better RR, not a smaller trade.

This is the concrete, simple form of "cycle within a cycle": **one bias TF (H4) + one execution TF (first LTF CF).** Generalizes to any (bias TF, execution TF) pair, always with HTF-anchored TP/SL.

---

## 5. Context dimensions every setup must carry

A CF is **not** context-free. Two CFs that look identical can mean opposite things. The tags we must read at the moment of action:

1. **CF ordinal — is it the 1st CF, 2nd CF, 3rd CF…?**
   - The position in the confirmation sequence changes the meaning (a 1st CF after a fresh VR ≠ a 3rd CF in an extended run).
2. **CF / setup LOCATION relative to the VR** *(new — not previously modeled):*
   - Is the CF **inside the VR**, **above the VR**, or **below the VR**?
   - Same CF, different location = **different context** (e.g. a CF firing back inside the VR is a different story than one firing beyond it).
3. **Bias-stack alignment at entry** — how many higher TFs (W1 / D1 / H4 / H1) are confirmed in the **same direction** at the instant of the execution CF.

These are **read from events that already printed** — they are context, not prediction.

---

## 6. Methodological guardrail (reactive ≠ undisciplined)

Being *reactive* does **not** waive sequencing discipline — it **defines** where the discipline lives:

- **Anchor every outcome measurement at the moment of reaction** (the execution CF you'd actually enter on), and measure **forward** from there.
- **Higher-TF context is fair game** as long as it was **confirmed in the past** relative to that entry instant. Reading "W1/D1/H4 are aligned sell" at entry is legitimate — those CFs already printed.
- **The one thing that is NOT allowed:** measuring an outcome over a window that **starts before the event you condition on existed** (e.g. crediting the move between an H4 CF and a later M5 CF to the M5 entry). That is hindsight, not reaction.
- In short: **reactive = anchor the stopwatch at the entry, never earlier.** With that anchor, the entire nested storyline above the entry is valid context.

*(This corrects the earlier "nesting is look-ahead, discard it" read — the nesting is kept; only the measurement anchor is fixed. See handover 2026-06-27.)*

---

## 7. Research questions this model generates

Each is measured **causally** (anchored at the execution CF, outcome forward) on the emitter event log (`tester_zones`):

1. **Which execution TF** gives the best risk-adjusted continuation when traded with its bias stack?
2. **How deep must the bias stack align** (W1 / D1 / H4 / H1 same-direction) before the execution-TF entry pays?
3. **CF ordinal effect** — does 1st vs 2nd vs nth CF change continuation?
4. **CF-vs-VR location effect** — inside / above / below the VR → does it change continuation?
5. **(bias TF, execution TF) pairing** — e.g. H4-bias + M5-trigger: does the lower-TF drop genuinely sharpen the entry vs the raw higher-TF CF?

> **Arbiter rule unchanged:** these are **selection screens** on emitter proxies (continued / realized_r). They decide **what to build**. The **MT5 strategy tester is the arbiter** of the actual money. ([[orb_unsorted_tick_lookahead]] discipline: anchor at entry, sort by event time, only join forward.)

---

## 8. What FOB is NOT

- ❌ A probabilistic classifier hunting a win-rate-lifting feature.
- ❌ A predictor of the next bar.
- ✅ A **reader of a confirmed, nested storyline** that picks **which cycle to trade** and **where in the story** to react.
