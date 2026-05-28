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


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_pipeline, tab_ideas, tab_cusum, tab_agents = st.tabs(["Pipeline", "Ideas", "CUSUM-001", "Agent Calls"])


# ── Tab 1: Pipeline ───────────────────────────────────────────────────────────

with tab_pipeline:
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
            colours = {"active": "background-color:#1a4a1a", "killed": "background-color:#4a1a1a", "parked": "background-color:#3a3a1a"}
            return colours.get(val, "")

        st.dataframe(
            pipeline_df.style.applymap(colour_status, subset=["stage_status"]),
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


# ── Tab 2: Ideas ──────────────────────────────────────────────────────────────

with tab_ideas:
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


# ── Tab 3: CUSUM-001 ──────────────────────────────────────────────────────────

with tab_cusum:
    cusum_dir = OUTPUTS_DIR / "cusum"

    plot1 = cusum_dir / "01_price_breakpoints.html"
    plot2 = cusum_dir / "02_vol_breakpoints.html"
    plot3 = cusum_dir / "03_regime_distributions.png"

    if not any([plot1.exists(), plot2.exists(), plot3.exists()]):
        st.info("No CUSUM-001 output yet. Run `python research/models/cusum/cusum.py` first.")
    else:
        if plot1.exists():
            st.subheader("Price + Breakpoints")
            st.components.v1.html(plot1.read_text(encoding="utf-8"), height=520, scrolling=False)

        if plot2.exists():
            st.subheader("Rolling Volatility + Breakpoints")
            st.components.v1.html(plot2.read_text(encoding="utf-8"), height=520, scrolling=False)

        if plot3.exists():
            st.subheader("Regime Return Distributions")
            st.image(str(plot3), use_container_width=True)

    st.divider()
    st.subheader("Logged Metrics")
    metrics_df = db_query(RESEARCH_DB, """
        SELECT metric_key, metric_value, metric_unit, test_type, timestamp, validate_summary
        FROM pipeline_events
        WHERE idea_id = 1 AND event_type = 'METRIC'
        ORDER BY timestamp DESC
    """)
    if metrics_df.empty:
        st.info("No metrics logged yet.")
    else:
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)


# ── Tab 4: Agent Calls ────────────────────────────────────────────────────────

with tab_agents:
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
            return "background-color:#2a1a4a" if val == "opus" else "background-color:#1a2a3a"

        def colour_gear(val):
            return "background-color:#1a3a2a" if val == "GENERATE" else "background-color:#3a2a1a"

        st.dataframe(
            agents_df.style
                .applymap(colour_model, subset=["model"])
                .applymap(colour_gear,  subset=["gear"]),
            use_container_width=True, hide_index=True
        )
        st.caption(f"{len(agents_df)} agent calls logged")

    st.divider()
    st.subheader("Papers Consulted")

    import json
    papers_df = db_query(AGENT_DB, """
        SELECT idea_code, gear, model, papers, timestamp
        FROM agent_calls
        WHERE papers != '[]' AND papers IS NOT NULL
        ORDER BY timestamp DESC
    """)

    if papers_df.empty:
        st.info("No papers logged yet.")
    else:
        rows = []
        for _, row in papers_df.iterrows():
            try:
                for p in json.loads(row["papers"]):
                    rows.append({
                        "idea":      row["idea_code"],
                        "gear":      row["gear"],
                        "model":     row["model"],
                        "title":     p.get("title", ""),
                        "url":       p.get("url", ""),
                        "source":    p.get("source", ""),
                        "relevance": p.get("relevance", ""),
                        "timestamp": row["timestamp"],
                    })
            except (json.JSONDecodeError, TypeError):
                continue

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No papers parsed yet.")
