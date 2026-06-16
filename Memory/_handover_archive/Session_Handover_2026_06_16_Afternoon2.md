# Handover — June 16, 2026 Afternoon2

## State
- **Paper agents SPLIT into two (FIND vs DISSECT):**
  - [quant-researcher.md](.claude/agents/quant-researcher.md) → pinned `model: sonnet`, FIND-only.
  - NEW [paper-dissector.md](.claude/agents/paper-dissector.md) → pinned `model: opus`, DISSECT-only (the "separate room" token firewall). Now registered + live.
  - Rationale: a skill/script can't replace the firewall (skills run in MAIN context). CLAUDE.md rules 5/5b rewritten; memory [feedback_hmm001_dissect_model.md] updated.
- **Singha 2025 "Forecast-to-Fill" (pid10) DISSECTED then re-filed BRK-001 → B2B-001** (files in [research/papers/b2b/](research/papers/b2b/) + DB via new `agent_log.reassign_paper()`). Dissect = log_agent call_id 73, artifact [singha_2025_forecast_to_fill_gold.dissect.md](research/papers/b2b/singha_2025_forecast_to_fill_gold.dissect.md).
- **Singha verdict:** trend/momentum vol-target Kelly on DAILY GC futures, NOT a range breakout. Its headline high-Sharpe is a vol-targeting artifact (tiny realized vol; the "43%/yr" = leverage scaling of a ~2.6%/yr real return). Exact figures + anchors in the [.dissect.md](research/papers/b2b/singha_2025_forecast_to_fill_gold.dissect.md) (log_agent call_id 73).
- **COST CLAIM CORRECTED:** earlier "JM 3–4× paper cost" was WRONG — JM Pro gold ~$0.20/oz RT ≈ 0.77–1.1 bps vs paper 0.7 bps (~1.1–1.6×); cost hits turnover (|Δw|≈0.066/day) so drag ~0.12%/yr. Cost does NOT kill it. Off-thesis + bull-only + tiny-abs-return are the real gates. Artifact + verdict fixed.
- **Sauce worth stealing for B2B-001:** vol-targeting + cost-aware Kelly (`g(f)=µf−½σ²f²−nkf−γ(nf)^1.5`, tempered 0.40×) as a risk/sizing LAYER on top of the B2B signal.
- All committed + pushed (master clean).

## Next
1. **Open Gate 2 for B2B-001** (still the P0): `pipeline.open_gate('B2B-001', 2, ...)`; build simplest B2B-retest detector on Arctic ticks ([arctic_io.py](research/code/arctic_io.py)) — existence test, not edge.
2. **Dissect Caporale&Plastun 2021** (pid8, task 59) via the NEW paper-dissector agent — `.md` already at [research/papers/b2b/caporale_2021_gold_oil_abnormal_returns.md](research/papers/b2b/caporale_2021_gold_oil_abnormal_returns.md).
3. STRUCT-001 P1s (74/75/76) if pivoting off B2B.

## Blockers
None.
