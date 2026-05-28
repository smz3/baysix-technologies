# Handover — May 28, 2026 Morning

## State
Research pipeline is fully built and schema-locked. Stage flow: `CAPTURED → HYPOTHESIS_SET → IS_SIGNAL → IS_BUILD → WALK_FORWARD → MONTE_CARLO → OOS → LIVE`. Migrations 001+002 applied. DB layer lives in `research/code/` (db_init, pipeline, ideas_log). CUSUM-001 module built at `research/models/cusum/cusum.py` — NOT YET RUN. Streamlit dashboard built at `research/dashboard/app.py` — NOT YET RUN. Visualization stack: Plotly (time series) + Seaborn (distributions) + Streamlit (unified platform). HMM-001 (idea_id=1) sits at `HYPOTHESIS_SET / active` in pipeline, pipeline_events is clean/empty.

## Next
1. Run CUSUM-001: `python research/models/cusum/cusum.py` — first run builds daily cache (~2 min), then detects breakpoints, saves 3 plots to `research/outputs/cusum/`
2. Verify output: K in range 6–12, March 2020 breakpoint present, CUSUM R² beats calendar year + random p99 benchmarks
3. Launch Streamlit dashboard: `streamlit run research/dashboard/app.py` — verify all 3 tabs (Pipeline, Ideas, CUSUM-001 plots)
4. If CUSUM-001 passes verification → advance HMM-001 to IS_SIGNAL via `pipeline.advance_stage(1, 'IS_SIGNAL', reason='...')`

## Blockers
None.
