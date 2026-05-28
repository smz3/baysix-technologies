# Handover — May 28, 2026 Afternoon2

## State
HMM-001 paper dissection in progress: 2/5 done. Papers 1 (arXiv:2007.14874 Oelschläger HHMM) and 2 (arXiv:2107.05535 Werge asset-independent HMM) fully dissected with proper [§X.X] citations in `research/db/agent_log.db`. Paper 2 required PyMuPDF crack (`py -3.12`, not `python`). QR agent hardened: domain-lock rule added, PyMuPDF fallback documented, orchestrator write checklist in place. Dashboard Papers tab: IDs now ascending, source shows `arxiv/XXXXXXX`, context_fit renders as numbered bullet points. CUSUM-001 `__pycache__` deleted, DB status fixed to `parked`. All committed and pushed (88855ba).

## Next
1. DISSECT paper ID=3 — arXiv:2006.08307 (HMM intraday momentum) — try HTML first, PyMuPDF fallback if needed
2. DISSECT paper ID=4 — arXiv:2402.05272 (Jump model) — has HTML experimental, should be clean
3. DISSECT paper ID=5 — arXiv:2412.03668 (HMM graphical + GH distributions) — has HTML experimental
4. After all 5 done: GENERATE brief (Sonnet) to lock 3 HMM-001 architecture decisions (K selection, emission feature set, stickiness mechanism)
5. Build `research/models/hmm/` — HMM-001 foundational model

## Blockers
None. PyMuPDF available via `py -3.12`. All 5 papers at known URLs in `papers_consulted`. DB and dashboard clean.
