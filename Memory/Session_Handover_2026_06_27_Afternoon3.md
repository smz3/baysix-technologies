# Handover — June 27, 2026 Afternoon3

## State
- **FOB-001 entry research pivoted to the CMP storyline-alignment model** (reaction modeling, NOT probabilistic). Concept + empirical findings locked in two specs: [storyline model](../docs/specs/2026-06-27_fob_cmp_storyline_model.md) + [alignment findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md).
- **Trader unchanged since v1.19.1.** Baselines: H1 = result_id 16 (net −0.363), H4 = result_id 17 (net −0.897). No new trader run this session.
- All work this session = **exploratory SELECTION screens on the emitter event log** (`tester_zones` run_id 5, 100,034 zones, ALL 8 TFs) — emitter proxy (`continued`/`realized_r`), **NOT MT5-net.** MT5 tester stays the money arbiter.
- Headline (numbers in [findings doc](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md), decision = `log_human_decision` call_id 88): storyline alignment = **durable hit-rate edge**; long-magnitude bias = **secular-bull confound**, not alpha.

## Next
1. **(task 188, P1)** Build full-stack alignment GATE into the H1 trader, MT5-net vs result_id 16. **Spec below.**
2. **(task 189, P2)** Genuine-bear confound test — run the storyline screen on a real gold bear (pre-2016 ticks / another asset); also sanity-check the `realized_r` directional convention.
3. **(parked)** H4 → first-LTF-CF execution model (HTF-anchored TP/SL — see Live-Threads).

**Task-188 spec (the main ask this session):**
- **Gate:** an H1 CF fires an entry ONLY when H4 AND D1 AND W1 *current alive bias* == CF direction (full-stack 3/3 of the H1 ladder).
- **State read:** trader reads its own higher-TF zone state at the H1-CF instant (emitter already tracks all 8 TFs; bias of TF h = direction of most-recent zone with confirm_time ≤ now AND not yet invalidated).
- **Hold everything else = id16 config** (InpSetupTf=H1, K=0.25, RMultTP=2.0, real ticks dukas) → a clean before/after on the SAME exec TF.
- **Compare** net/trade vs result_id 16 (−0.363). Expect far fewer trades (~1,383 of 5,289 H1 CFs are full-stack) + higher WR. Log via `pipeline.log_result`.

## Blockers
- None.

## Why
- **Entry is the lever (result_id 16):** 2:1 payoff already clean, the whole deficit is hit-rate. Storyline alignment is the **first causal signal that lifts hit-rate durably** → it's what to take to the trader.
- **Chose directional alignment over spatial nesting:** nesting (inner CF inside outer zone) was flat on hit-rate; directional bias-stack alignment is the real signal ([findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) §1–2). The earlier "+14pp" Framing A was look-ahead (outer conditioned on a *future* child) — discarded.
- **Reactive guardrail (the methodology fix):** anchor the outcome stopwatch at the entry CF and measure forward; read higher-TF bias from PAST-confirmed alive zones. Reactive ≠ undisciplined — it just defines where the anchor sits ([model doc](../docs/specs/2026-06-27_fob_cmp_storyline_model.md) §6).
- **All 8 TF baselines already exist in the emitter** (run_id 5) — that's what the screens ran on. No need to run more emitter data.

## Ruled-Out
- **Spatial nesting as the entry signal** — flat hit-rate ([findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) §1). Containment is not the edge; directional alignment is.
- **Running M5/D1/W1/MN1 trader baselines** — D1/W1/MN1 have too few setups (240/38/9 confirmed zones in 8yr) to be EXECUTION TFs; they are BIAS inputs only. M5 = smallest lift + known raw-entry blow-up risk. Don't spray baselines — the missing piece is MT5-net of the H1 gate, not more raw data.
- **Long-bias payoff as validated alpha** — confounded with gold's secular bull; SELL `realized_r` stays negative even in DOWN regimes, and 2016–2024 has NO genuine bear ([findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) §4). Do NOT hard-code a long bias.

## Live-Threads
- **LTF-execution caveat (Syafiq, this session):** when a lower TF *triggers* an HTF CF, **TP uses HTF logic and SL sits at the HTF CF zone** — the LTF only sharpens entry timing/price, it does NOT shrink the trade to an LTF target/stop. Preserves HTF payoff structure → better RR, not a smaller trade. Captured in [model doc](../docs/specs/2026-06-27_fob_cmp_storyline_model.md) §4; belongs to the parked H4→first-LTF-CF model.
- **`realized_r` directional convention** — BUY always positive, SELL always negative, even in DOWN regimes. Either gold's bull OR an emitter measurement asymmetry for shorts. Sanity-check inside task 189.
- **CF ordinal (1st/2nd/nth) + CF-vs-VR location (inside/above/below)** — two context dims identified but NOT yet screened. Cheap next screens on run_id 5 if the alignment gate validates.
- **Hit-rate lift concentrates at higher exec TFs** (H1 > M30 > M15 > M5) — dropping to LTF buys precision/RR, not hit-rate. Informs the parked LTF-execution model.
