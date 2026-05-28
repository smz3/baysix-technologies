# Handover — May 28, 2026 Afternoon

## State
Research infrastructure significantly upgraded and pushed to master (820c6d2). All SQLite DBs moved to `research/db/` (ideas_log, research_log, agent_log). QR agent upgraded with Step 0 context loading, WebSearch/SSRN protocol, mandatory Papers Consulted block, and Opus/Sonnet selection rules (Rule 12 in CLAUDE.md). Streamlit dashboard running at localhost:8501 with new Agent Calls tab. CUSUM-001 is parked — over-segmentation issue (l2/rbf mismatch) identified but not fully fixed; decision made to skip CUSUM as HMM gatekeeper and move directly to HMM-001. Research pipeline and agent_calls tables are empty/clean.

## Next
1. Test agent_calls logging end-to-end: brief QR agent (Sonnet, GENERATE gear) on HMM-001 foundations — have it pull ArXiv papers on HMM for financial regime detection, verify Papers Consulted block logs cleanly to `research/db/agent_log.db`
2. Build `research/models/hmm/` — HMM-001 foundational model (Gaussian emissions, 2–4 hidden states, fit on XAUUSD IS daily log returns 2016–2024-05-02)
3. Add `layer` column to `build_order` table in ideas_log.db to tag: core_infra / infra_filter / strategy / deployment / scale

## Blockers
None — pipeline clean, all paths verified, git pushed.
