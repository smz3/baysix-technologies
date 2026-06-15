# Handover — June 15, 2026 Evening

## State
- **NEXT-SESSION PRIORITY: dissect the B2B keeper papers on Opus** (tasks 99/100/101 + 59). Reverse-search session — found published prior-art that VALIDATES the strategy we already trade, instead of top-down ideas that keep getting killed.
- **TDA-001 registered + PARKED.** Gidea & Katz 2017 topology/persistent-homology crash paper dissected full-text on Opus (call_id 68, paper_id 27). Verdict: it's a cross-sectional, daily, ~1yr-horizon multi-asset crash detector — B2B analogy is mostly metaphor (5-pointer ≠ homology loop). Cheapest revival test = plain rolling realized-variance/kurtosis on XAUUSD BEFORE any homology code (paper proves L^p-norm ∝ variance). Not pursuing now.
- **B2B-001 idea created** (strategy, parent STRUCT-001) — "Sigma B2B Structural Zone Strategy", to be built FRESH on STRUCT-001 (not b2b/sigma_core).
- **B2B FIND logged** under STRUCT-001 (call_id 69, Sonnet): 10 ranked papers, 4 keepers.
- **3 keepers registered in step2_papers under B2B-001:** pid28 Osler 2003 (FX order-book stop-clustering=L1/cascade, CONFIRMS retest), pid29 Chung & Bellotti 2021 (SR bounce-prob decays w/ age → zone lifecycle), pid30 Costa 2026 (gold confirms breakouts >66% vs FX reverts >75% → CHALLENGES B2B reversion on XAUUSD; highest-impact). 4th keeper Caporale & Plastun 2021 already = pid8/BRK-001/task 59.
- **PDFs:** new folder [research/papers/b2b/](research/papers/b2b/). Osler (133KB) + Chung (527KB) downloaded via [fetch_papers.py](research/code/fetch_papers.py) (manifest extended). Costa SSRN-blocked (HTTP 403) → NOT on disk.

## Next
1. **Download Costa 2026 manually** (SSRN bot-wall): open https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6592020 logged-in, save as research/papers/b2b/costa_2026_illusion_of_breakouts.pdf (task 101).
2. **Dissect on Opus (QR agent), one per task:** Osler 2003 (task 99), Chung & Bellotti 2021 (task 100), Costa 2026 (task 101, after download), Caporale & Plastun (task 59). Log each via `log_dissect_result()`.
3. After dissects: synthesize whether lit confirms B2B retest edge on XAUUSD (esp. Costa's gold-trend challenge) → decide B2B-001 Gate 0/1 framing.

## Blockers
None hard. Costa PDF needs manual SSRN download before its dissect (task 101).

## Notes
- TDA files moved to [research/papers/tda/](research/papers/tda/) (were briefly under b2b/). pid27 DB `local_path` still points at the old papers/ root path — stale but harmless (TDA-001 parked, dissect already logged; no sanctioned update_paper in code layer, raw-sqlite3 blocked by protocol_guard).
