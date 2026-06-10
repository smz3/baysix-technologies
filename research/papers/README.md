# Research Paper PDFs (local-only)

Drop source PDFs of papers here for local dissection. **PDFs are gitignored**
(`*.pdf`) — copyright + binary bloat. Only this README is tracked.

The *dissection* (key equations, empirical findings, context-fit, limitations)
is the durable artifact and lives in `research.db` → `step2_papers`, written via
`agent_log.log_dissect_result()`. The PDF is just transient input for the read.

**Naming:** `<firstauthor>_<year>_<shorttitle>.pdf`
e.g. `baltussen_2021_hedging_demand.pdf`

Workflow when SSRN/journal is bot-blocked: download the PDF in a logged-in
browser → save it here → Claude extracts text locally (PyMuPDF) → re-runs the
Opus DISSECT with the text passed inline → logs the result to `step2_papers`.
