"""
Baysix Research Dashboard — Streamlit
Run: streamlit run research/dashboard/app.py
"""

import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH     = Path(__file__).parents[1] / "db" / "research.db"
OUTPUTS_DIR = Path(__file__).parents[0].parent / "outputs"

st.set_page_config(page_title="Baysix Research", layout="wide", page_icon="B")
st.title("Baysix Research Dashboard")


def q(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def safe_style(df, style_map):
    styler = df.style
    for col, fn in style_map.items():
        if col in df.columns:
            styler = styler.map(fn, subset=[col])
    return styler


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_lifecycle, tab_gates, tab_ideas, tab_results, tab_agents, tab_papers = st.tabs([
    "Lifecycle", "Gates", "Ideas", "Results", "Agent Calls", "Papers"
])


# ── Tab 1: Lifecycle ──────────────────────────────────────────────────────────

with tab_lifecycle:
    try:
        st.subheader("Idea Lifecycle — Command Centre")
        df = q("SELECT * FROM idea_lifecycle ORDER BY idea_id")

        if df.empty:
            st.info("No ideas yet.")
        else:
            def colour_status(val):
                return {
                    "graduated": "background-color:#1a4a1a",
                    "killed":    "background-color:#4a1a1a",
                    "ideation":  "background-color:#1a2a3a",
                }.get(str(val), "")

            st.dataframe(
                safe_style(df, {"status": colour_status}),
                use_container_width=True, hide_index=True
            )
            total     = len(df)
            graduated = int((df["status"] == "graduated").sum())
            killed    = int((df["status"] == "killed").sum())
            active    = total - graduated - killed
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Ideas",  total)
            c2.metric("Active",       active)
            c3.metric("Graduated",    graduated)
            c4.metric("Killed",       killed)

    except Exception as e:
        st.error(f"Lifecycle tab error: {e}")


# ── Tab 2: Gates ──────────────────────────────────────────────────────────────

with tab_gates:
    try:
        st.subheader("Gate Pipeline — Stuck Ideas")
        stuck = q("SELECT * FROM gate_pipeline")
        if stuck.empty:
            st.success("No ideas stuck at any gate.")
        else:
            def colour_gate_status(val):
                return {
                    "open":    "background-color:#1a2a3a",
                    "blocked": "background-color:#4a3a1a",
                }.get(str(val), "")
            st.dataframe(
                safe_style(stuck, {"gate_status": colour_gate_status}),
                use_container_width=True, hide_index=True
            )

        st.divider()
        st.subheader("Gate Detail — All Gates by Idea")

        ideas = q("SELECT idea_id, name FROM step1_ideas ORDER BY idea_id")
        if not ideas.empty:
            selected = st.selectbox("Select idea", ideas["idea_id"].tolist())
            gates_df = q(
                "SELECT gate_number, attempt, status, gate_question, gate_answer, pass_criteria, answered_by, answered_at FROM step3_gates WHERE idea_id=? ORDER BY gate_number, attempt",
                (selected,)
            )
            if gates_df.empty:
                st.info("No gates opened yet for this idea.")
            else:
                def colour_gate(val):
                    return {
                        "passed":  "background-color:#1a4a1a",
                        "killed":  "background-color:#4a1a1a",
                        "blocked": "background-color:#4a3a1a",
                        "open":    "background-color:#1a2a3a",
                    }.get(str(val), "")
                st.dataframe(
                    safe_style(gates_df, {"status": colour_gate}),
                    use_container_width=True, hide_index=True
                )

    except Exception as e:
        st.error(f"Gates tab error: {e}")


# ── Tab 3: Ideas ──────────────────────────────────────────────────────────────

with tab_ideas:
    try:
        c1, c2 = st.columns(2)
        with c1:
            status_filter = st.selectbox("Status", ["all", "ideation", "gate_0", "gate_1", "gate_2", "gate_3", "gate_4", "gate_5", "gate_6", "graduated", "killed"])
        with c2:
            cat_filter = st.selectbox("Category", ["all", "regime", "signal", "execution", "risk"])

        query  = "SELECT idea_id, name, category, parent_idea_id, status, created_at FROM step1_ideas WHERE 1=1"
        params = []
        if status_filter != "all":
            query += " AND status=?"; params.append(status_filter)
        if cat_filter != "all":
            query += " AND category=?"; params.append(cat_filter)
        query += " ORDER BY idea_id"

        ideas_df = q(query, params)
        st.dataframe(ideas_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(ideas_df)} ideas shown")

    except Exception as e:
        st.error(f"Ideas tab error: {e}")


# ── Tab 4: Results ────────────────────────────────────────────────────────────

with tab_results:
    try:
        st.subheader("Model Outputs")

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
        st.subheader("Logged Metrics — step4_results")

        metrics_df = q("""
            SELECT r.idea_id, r.gate_number, r.stage, r.metric_key,
                   r.metric_value, r.cost_adjusted, r.period,
                   r.n_obs, r.instrument, r.logged_at
            FROM step4_results r
            ORDER BY r.logged_at DESC
        """)
        if metrics_df.empty:
            st.info("No metrics logged yet.")
        else:
            def colour_cost(val):
                return "background-color:#1a4a1a" if val == 1 else "background-color:#3a1a1a"
            st.dataframe(
                safe_style(metrics_df, {"cost_adjusted": colour_cost}),
                use_container_width=True, hide_index=True
            )

    except Exception as e:
        st.error(f"Results tab error: {e}")


# ── Tab 5: Agent Calls ────────────────────────────────────────────────────────

with tab_agents:
    try:
        st.subheader("QR Agent Run Log")

        agents_df = q("""
            SELECT call_id, idea_id, gate_number, gear, model, task_summary, created_at
            FROM log_agent
            ORDER BY created_at DESC
        """)

        if agents_df.empty:
            st.info("No agent calls logged yet.")
        else:
            def colour_model(val):
                return "background-color:#2a1a4a" if str(val).lower() == "opus" else "background-color:#1a2a3a"

            def colour_gear(val):
                return {
                    "GENERATE": "background-color:#1a3a2a",
                    "DISSECT":  "background-color:#2a1a4a",
                    "VALIDATE": "background-color:#3a2a1a",
                }.get(str(val), "")

            st.dataframe(
                safe_style(agents_df, {"model": colour_model, "gear": colour_gear}),
                use_container_width=True, hide_index=True
            )
            st.caption(f"{len(agents_df)} agent calls logged")

    except Exception as e:
        st.error(f"Agent Calls tab error: {e}")


# ── Tab 6: Papers ─────────────────────────────────────────────────────────────

with tab_papers:
    try:
        all_papers = q("""
            SELECT p.paper_id, p.idea_id, p.title, p.authors, p.year,
                   p.source, p.url, p.dissected,
                   p.key_equations, p.empirical_findings,
                   p.context_fit, p.limitations,
                   p.added_at, p.dissected_at
            FROM step2_papers p
            ORDER BY p.paper_id ASC
        """)

        total     = len(all_papers)
        dissected = int(all_papers["dissected"].sum()) if not all_papers.empty else 0
        pending   = total - dissected

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Papers",       total)
        m2.metric("Dissected",          dissected)
        m3.metric("Pending Dissection", pending)

        st.divider()

        if all_papers.empty:
            st.info("No papers in the knowledge base yet.")
        else:
            f1, f2, f3 = st.columns(3)
            with f1:
                idea_opts   = ["all"] + sorted(all_papers["idea_id"].dropna().unique().tolist())
                idea_filter = st.selectbox("Idea", idea_opts)
            with f2:
                src_opts   = ["all"] + sorted(all_papers["source"].dropna().unique().tolist())
                src_filter = st.selectbox("Source", src_opts)
            with f3:
                dissect_filter = st.selectbox("Dissected", ["all", "yes", "no"])

            df = all_papers.copy()
            if idea_filter != "all":
                df = df[df["idea_id"] == idea_filter]
            if src_filter != "all":
                df = df[df["source"] == src_filter]
            if dissect_filter == "yes":
                df = df[df["dissected"] == 1]
            elif dissect_filter == "no":
                df = df[df["dissected"] == 0]

            st.caption(f"{len(df)} paper(s) shown")

            summary_cols = ["paper_id", "idea_id", "source", "title", "dissected", "added_at", "dissected_at"]
            available    = [c for c in summary_cols if c in df.columns]

            def badge_dissected(val):
                return "background-color:#1a3a2a" if val == 1 else "background-color:#3a1a1a"

            st.dataframe(
                safe_style(df[available], {"dissected": badge_dissected}),
                use_container_width=True, hide_index=True,
            )

            st.divider()
            st.subheader("Paper Detail")

            if not df.empty:
                paper_labels  = [f"[{row['paper_id']}] {row['title'][:70]}" for _, row in df.iterrows()]
                selected_label = st.selectbox("Select paper", paper_labels)
                selected_id    = int(selected_label.split("]")[0].strip("["))
                paper          = df[df["paper_id"] == selected_id].iloc[0]

                st.markdown(f"### {paper['title']}")
                if paper.get("url"):
                    st.markdown(f"**URL:** [{paper['url']}]({paper['url']})")
                st.markdown(
                    f"**Idea:** {paper['idea_id']}  |  "
                    f"**Source:** {paper.get('source', '—')}  |  "
                    f"**Dissected:** {'Yes' if paper['dissected'] else 'No'}"
                )
                st.divider()

                def render_field(label, value):
                    has_content = value is not None and str(value).strip() not in ("", "None")
                    with st.expander(label, expanded=has_content):
                        if has_content:
                            st.markdown(str(value))
                        else:
                            st.caption("Not yet populated — run DISSECT gear to fill this field.")

                render_field("Key Equations",      paper.get("key_equations"))
                render_field("Empirical Findings", paper.get("empirical_findings"))
                render_field("Context Fit",        paper.get("context_fit"))
                render_field("Limitations",        paper.get("limitations"))

    except Exception as e:
        st.error(f"Papers tab error: {e}")
