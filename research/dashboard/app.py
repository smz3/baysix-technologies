"""
Baysix Research Dashboard — Streamlit
Run: streamlit run research/dashboard/app.py
"""

import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

IDEAS_DB    = Path(__file__).parents[1] / "db" / "ideas_log.db"
RESEARCH_DB = Path(__file__).parents[1] / "db" / "research_log.db"
AGENT_DB    = Path(__file__).parents[1] / "db" / "agent_log.db"
OUTPUTS_DIR = Path(__file__).parents[0].parent / "outputs"

st.set_page_config(page_title="Baysix Research", layout="wide", page_icon="B")
st.title("Baysix Research Dashboard")


def db_query(db_path, query, params=(), attach=None):
    conn = sqlite3.connect(db_path)
    if attach:
        for alias, path in attach.items():
            conn.execute(f"ATTACH DATABASE '{path}' AS {alias}")
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def safe_style(df, style_map):
    """Apply column colouring safely — skips columns that don't exist in df."""
    styler = df.style
    for col, fn in style_map.items():
        if col in df.columns:
            styler = styler.map(fn, subset=[col])
    return styler


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_pipeline, tab_ideas, tab_models, tab_agents, tab_papers = st.tabs(
    ["Pipeline", "Ideas", "Model Outputs", "Agent Calls", "Papers"]
)


# ── Tab 1: Pipeline ───────────────────────────────────────────────────────────

with tab_pipeline:
    try:
        st.subheader("Active Pipeline")

        pipeline_df = db_query(RESEARCH_DB, """
            SELECT
                p.idea_id,
                i.code,
                i.name,
                p.current_stage,
                p.stage_status,
                p.asset_class,
                p.approach,
                p.gross_metric,
                p.net_metric,
                p.updated_at
            FROM pipeline p
            LEFT JOIN ideas_db.ideas i ON p.idea_id = i.id
            ORDER BY p.idea_id
        """, attach={"ideas_db": str(IDEAS_DB)})

        if pipeline_df.empty:
            st.info("No ideas in pipeline yet.")
        else:
            def colour_status(val):
                return {
                    "active": "background-color:#1a4a1a",
                    "killed": "background-color:#4a1a1a",
                    "parked": "background-color:#3a3a1a",
                }.get(val, "")

            st.dataframe(
                safe_style(pipeline_df, {"stage_status": colour_status}),
                use_container_width=True, hide_index=True
            )

        st.divider()
        st.subheader("Event History")

        idea_codes = pipeline_df["code"].tolist() if not pipeline_df.empty else []
        selected   = st.selectbox("Select idea", idea_codes) if idea_codes else None

        if selected:
            idea_id = int(pipeline_df[pipeline_df["code"] == selected]["idea_id"].iloc[0])
            events_df = db_query(RESEARCH_DB, """
                SELECT event_type, from_stage, to_stage, metric_key,
                       metric_value, metric_unit, test_type, triggered_by, reason, timestamp
                FROM pipeline_events
                WHERE idea_id = ?
                ORDER BY timestamp
            """, (idea_id,))

            if events_df.empty:
                st.info("No events logged yet.")
            else:
                st.dataframe(events_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Pipeline tab error: {e}")


# ── Tab 2: Ideas ──────────────────────────────────────────────────────────────

with tab_ideas:
    try:
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status", ["all", "inbox", "promoted", "parked", "dropped"])
        with col2:
            role_filter = st.selectbox("Role", ["all", "infrastructure", "strategy"])
        with col3:
            cat_filter = st.selectbox("Category", ["all", "alpha", "regime", "guard", "signal_processing", "execution", "cost_utility", "diagnostic"])

        query = "SELECT id, code, name, role, category, status, asset_class, created_at FROM ideas WHERE 1=1"
        params = []
        if status_filter != "all":
            query += " AND status = ?"; params.append(status_filter)
        if role_filter != "all":
            query += " AND role = ?"; params.append(role_filter)
        if cat_filter != "all":
            query += " AND category = ?"; params.append(cat_filter)
        query += " ORDER BY sort_order, id"

        ideas_df = db_query(IDEAS_DB, query, params)
        st.dataframe(ideas_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(ideas_df)} ideas shown")

        st.divider()
        st.subheader("Build Order")
        build_df = db_query(IDEAS_DB, "SELECT * FROM build_order ORDER BY phase, sequence")
        st.dataframe(build_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Ideas tab error: {e}")


# ── Tab 3: Model Outputs ──────────────────────────────────────────────────────

with tab_models:
    try:
        st.subheader("Model Outputs")
        st.caption("One section per built model. Add a section here when a new model produces output plots.")

        cusum_dir = OUTPUTS_DIR / "cusum"
        plot1 = cusum_dir / "01_price_breakpoints.html"
        plot2 = cusum_dir / "02_vol_breakpoints.html"
        plot3 = cusum_dir / "03_regime_distributions.png"

        with st.expander("CUSUM-001 — Structural Break Detector (parked)", expanded=False):
            if not any([plot1.exists(), plot2.exists(), plot3.exists()]):
                st.info("No output yet.")
            else:
                if plot1.exists():
                    st.markdown("**Price + Breakpoints**")
                    st.components.v1.html(plot1.read_text(encoding="utf-8"), height=520, scrolling=False)
                if plot2.exists():
                    st.markdown("**Rolling Volatility + Breakpoints**")
                    st.components.v1.html(plot2.read_text(encoding="utf-8"), height=520, scrolling=False)
                if plot3.exists():
                    st.markdown("**Regime Return Distributions**")
                    st.image(str(plot3), use_container_width=True)

        st.divider()
        st.subheader("Logged Metrics")
        metrics_df = db_query(RESEARCH_DB, """
            SELECT i.code, pe.metric_key, pe.metric_value, pe.metric_unit,
                   pe.test_type, pe.timestamp, pe.validate_summary
            FROM pipeline_events pe
            LEFT JOIN ideas_db.ideas i ON pe.idea_id = i.id
            WHERE pe.event_type = 'METRIC'
            ORDER BY pe.timestamp DESC
        """, attach={"ideas_db": str(IDEAS_DB)})

        if metrics_df.empty:
            st.info("No metrics logged yet.")
        else:
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Model Outputs tab error: {e}")


# ── Tab 4: Agent Calls ────────────────────────────────────────────────────────

with tab_agents:
    try:
        st.subheader("QR Agent Run Log")

        agents_df = db_query(AGENT_DB, """
            SELECT id, idea_code, gear, model, task, timestamp
            FROM agent_calls
            ORDER BY timestamp DESC
        """)

        if agents_df.empty:
            st.info("No agent calls logged yet.")
        else:
            def colour_model(val):
                return "background-color:#2a1a4a" if str(val).lower() == "claude-opus-4-6" else "background-color:#1a2a3a"

            def colour_gear(val):
                return {
                    "GENERATE": "background-color:#1a3a2a",
                    "DISSECT":  "background-color:#2a1a4a",
                    "VALIDATE": "background-color:#3a2a1a",
                }.get(val, "")

            st.dataframe(
                safe_style(agents_df, {"model": colour_model, "gear": colour_gear}),
                use_container_width=True, hide_index=True
            )
            st.caption(f"{len(agents_df)} agent calls logged")

    except Exception as e:
        st.error(f"Agent Calls tab error: {e}")


# ── Tab 5: Papers ─────────────────────────────────────────────────────────────

with tab_papers:
    try:
        all_papers = db_query(AGENT_DB, """
            SELECT
                p.id, p.agent_call_id, p.title, p.url, p.source,
                p.relevance, p.abstract, p.key_equations, p.empirical_findings,
                p.context_fit, p.limitations, p.replication_status,
                p.dissected, p.timestamp,
                a.idea_code, a.gear
            FROM papers_consulted p
            LEFT JOIN agent_calls a ON p.agent_call_id = a.id
            ORDER BY p.id ASC
        """)

        total      = len(all_papers)
        dissected  = int(all_papers["dissected"].sum()) if not all_papers.empty else 0
        pending    = total - dissected
        replicated = int((all_papers["replication_status"] != "none").sum()) if not all_papers.empty else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Papers",       total)
        m2.metric("Dissected",          dissected)
        m3.metric("Pending Dissection", pending)
        m4.metric("Replicated",         replicated)

        st.divider()

        if all_papers.empty:
            st.info("No papers in the knowledge base yet. Run a GENERATE brief to pull papers.")
        else:
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                idea_opts = ["all"] + sorted(all_papers["idea_code"].dropna().unique().tolist())
                idea_filter = st.selectbox("Idea", idea_opts)
            with f2:
                src_opts = ["all"] + sorted(all_papers["source"].dropna().unique().tolist())
                src_filter = st.selectbox("Source", src_opts)
            with f3:
                dissect_filter = st.selectbox("Dissected", ["all", "yes", "no"])
            with f4:
                rep_opts = ["all", "none", "attempted", "confirmed", "upgraded"]
                rep_filter = st.selectbox("Replication", rep_opts)

            df = all_papers.copy()
            if idea_filter != "all":
                df = df[df["idea_code"] == idea_filter]
            if src_filter != "all":
                df = df[df["source"] == src_filter]
            if dissect_filter == "yes":
                df = df[df["dissected"] == 1]
            elif dissect_filter == "no":
                df = df[df["dissected"] == 0]
            if rep_filter != "all":
                df = df[df["replication_status"] == rep_filter]

            st.caption(f"{len(df)} paper(s) shown")

            def _fmt_source(row):
                src = str(row.get("source") or "").lower()
                url = str(row.get("url") or "")
                paper_id = url.rstrip("/").split("/")[-1] if url else ""
                return f"{src}/{paper_id}" if paper_id else src

            df["source_display"] = df.apply(_fmt_source, axis=1)

            summary_cols = ["id", "idea_code", "gear", "source_display", "title", "dissected", "replication_status", "timestamp"]
            available = [c for c in summary_cols if c in df.columns]

            def badge_dissected(val):
                return "background-color:#1a3a2a" if val == 1 else "background-color:#3a1a1a"

            def badge_rep(val):
                return {
                    "none":      "",
                    "attempted": "background-color:#3a3a1a",
                    "confirmed": "background-color:#1a3a2a",
                    "upgraded":  "background-color:#2a1a4a",
                }.get(str(val), "")

            st.dataframe(
                safe_style(df[available], {"dissected": badge_dissected, "replication_status": badge_rep}),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("Paper Detail")

            if df.empty:
                st.info("No papers match the current filters.")
            else:
                paper_labels = [f"[{row['id']}] {row['title'][:70]}" for _, row in df.iterrows()]
                selected_label = st.selectbox("Select paper", paper_labels)
                selected_id = int(selected_label.split("]")[0].strip("["))
                paper = df[df["id"] == selected_id].iloc[0]

                st.markdown(f"### {paper['title']}")
                st.markdown(
                    f"**Source:** {str(paper['source']).upper()}  |  "
                    f"**URL:** [{paper['url']}]({paper['url']})"
                )
                st.markdown(
                    f"**Idea:** {paper['idea_code']}  |  "
                    f"**Gear:** {paper['gear']}  |  "
                    f"**Dissected:** {'Yes' if paper['dissected'] else 'No'}  |  "
                    f"**Replication:** {paper['replication_status']}"
                )

                st.divider()

                def render_field(label, value):
                    has_content = value is not None and str(value).strip() not in ("", "None")
                    with st.expander(label, expanded=has_content):
                        if has_content:
                            st.markdown(str(value))
                        else:
                            st.caption("Not yet populated — run DISSECT gear to fill this field.")

                render_field("Relevance",          paper.get("relevance"))
                render_field("Abstract",           paper.get("abstract"))
                render_field("Key Equations",      paper.get("key_equations"))
                render_field("Empirical Findings", paper.get("empirical_findings"))
                render_field("Context Fit",        paper.get("context_fit"))
                render_field("Limitations",        paper.get("limitations"))

    except Exception as e:
        st.error(f"Papers tab error: {e}")
