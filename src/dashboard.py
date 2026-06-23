"""
Module 5 — Operations Dashboard
================================
Streamlit web interface for facility overseers to monitor compliance status,
review alerts, and export audit records.

Views:
  A. Live Feed Monitor — Upload & analyze video clips in real time
  B. Alert Timeline    — Chronological stream of HIGH/CRITICAL events
  C. Historical Log    — Filterable table with date range, severity, behavior + CSV export

Run:
  streamlit run src/dashboard.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta

# Add parent folder to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.reports import init_database, get_all_violations, export_to_csv, get_summary_stats, save_violation
from src.severity import enrich_violation
# Note: detection functions are imported lazily inside the button handler

# ─── PAGE CONFIG ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Factory Compliance Dashboard",
    page_icon="🏭",
    layout="wide"
)

# ─── CUSTOM STYLING ────────────────────────────────────────────────
st.markdown("""
<style>
.critical { background-color: #7f1d1d; color: #fecaca; padding: 4px 10px;
            border-radius: 6px; font-weight: 600; font-size: 12px; }
.high     { background-color: #78350f; color: #fde68a; padding: 4px 10px;
            border-radius: 6px; font-weight: 600; font-size: 12px; }
.medium   { background-color: #1e3a5f; color: #bfdbfe; padding: 4px 10px;
            border-radius: 6px; font-weight: 600; font-size: 12px; }
.low      { background-color: #14532d; color: #bbf7d0; padding: 4px 10px;
            border-radius: 6px; font-weight: 600; font-size: 12px; }
.status-safe {
    background-color: #14532d; color: #bbf7d0; padding: 8px 16px;
    border-radius: 8px; font-weight: 600; font-size: 14px;
    text-align: center; margin: 8px 0;
}
.status-violation {
    background-color: #7f1d1d; color: #fecaca; padding: 8px 16px;
    border-radius: 8px; font-weight: 600; font-size: 14px;
    text-align: center; margin: 8px 0;
}
.status-pending {
    background-color: #1e3a5f; color: #bfdbfe; padding: 8px 16px;
    border-radius: 8px; font-weight: 600; font-size: 14px;
    text-align: center; margin: 8px 0;
}
.alert-banner {
    background-color: #7f1d1d;
    border: 2px solid #ef4444;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
    animation: pulse 1s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
</style>
""", unsafe_allow_html=True)

# ─── INIT ─────────────────────────────────────────────────────────
init_database()

# ─── SIDEBAR ──────────────────────────────────────────────────────
st.sidebar.title("🏭 Compliance System")
st.sidebar.markdown("**TechGenesys Factory Safety**")

view = st.sidebar.radio(
    "Navigation",
    ["📹 Live Feed Monitor", "🚨 Alert Timeline", "📊 Historical Log"]
)

# ─── STATS ROW ────────────────────────────────────────────────────
stats = get_summary_stats()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🔴 Critical", stats.get("CRITICAL", 0))
with col2:
    st.metric("🟠 High", stats.get("HIGH", 0))
with col3:
    st.metric("🟡 Medium", stats.get("MEDIUM", 0))
with col4:
    st.metric("🟢 Low", stats.get("LOW", 0))

st.divider()

# ─── VIEW A: LIVE FEED MONITOR ────────────────────────────────────
if view == "📹 Live Feed Monitor":
    st.header("📹 Live Feed Monitor")

    col_upload_1, col_upload_2 = st.columns(2)
    with col_upload_1:
        uploaded_policy = st.file_uploader(
            "Upload Policy Document (PDF)",
            type=["pdf"]
        )
    with col_upload_2:
        uploaded_video = st.file_uploader(
            "Upload a video clip to analyze",
            type=["mp4", "avi", "mov"]
        )

    if uploaded_policy and uploaded_video:
        # Save uploaded files temporarily
        temp_policy_path = f"data/temp_{uploaded_policy.name}"
        temp_video_path = f"data/temp_{uploaded_video.name}"
        os.makedirs("data", exist_ok=True)
        
        with open(temp_policy_path, "wb") as f:
            f.write(uploaded_policy.read())
        with open(temp_video_path, "wb") as f:
            f.write(uploaded_video.read())

        # Two-column layout: video on left, status on right
        vid_col, status_col = st.columns([2, 1])

        with vid_col:
            st.video(temp_video_path)

        with status_col:
            # Status indicator — starts as "Pending Analysis"
            if "analysis_done" not in st.session_state:
                st.session_state.analysis_done = False
                st.session_state.analysis_results = []

            if not st.session_state.analysis_done:
                st.markdown('<div class="status-pending">⏳ PENDING ANALYSIS</div>',
                            unsafe_allow_html=True)
                st.caption("Click 'Analyze' to run compliance detection")
            elif st.session_state.analysis_results:
                st.markdown('<div class="status-violation">🚨 VIOLATION DETECTED</div>',
                            unsafe_allow_html=True)
                for v in st.session_state.analysis_results:
                    level = v["severity"].lower()
                    st.markdown(f'<span class="{level}">{v["severity"]}</span> '
                                f'**{v["behavior_class"]}**', unsafe_allow_html=True)
                    st.caption(f'{v["zone"]} — {v["description"][:80]}...')
            else:
                st.markdown('<div class="status-safe">✅ NO VIOLATION DETECTED</div>',
                            unsafe_allow_html=True)

        if st.button("🔍 Analyze for Violations", type="primary"):
            with st.spinner("Parsing Policy and Running Detection..."):
                # 1. Parse Policy
                from src.parse_policy import extract_policy_rules
                from src.severity import reload_severity_map
                
                extract_policy_rules(temp_policy_path)
                reload_severity_map()
                
                # 2. Run Video Detection
                from src.detection import classify_video, load_model
                model, device = load_model()
                v = classify_video(temp_video_path, model, device)
                violations = [v] if v else []

                # Enrich with severity (Module 2)
                enriched = [enrich_violation(v) for v in violations]

                # Save to DB (Module 4) and Trigger Escalation (Module 3)
                from src.escalation import trigger_escalation
                for v in enriched:
                    save_violation(v)
                    trigger_escalation(v)

            # Update session state for status indicator
            st.session_state.analysis_done = True
            st.session_state.analysis_results = enriched

            if enriched:
                # Check if any are HIGH/CRITICAL for alert banner (Module 3 visual alert)
                critical_found = [v for v in enriched if v["severity"] in ["HIGH", "CRITICAL"]]

                if critical_found:
                    st.markdown(f"""
                    <div class="alert-banner">
                        🚨 <strong>ALERT — {len(critical_found)} HIGH/CRITICAL violation(s) detected!</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    # Play browser alert sound via JS
                    st.markdown("""
                    <script>
                    const ctx = new AudioContext();
                    const oscillator = ctx.createOscillator();
                    oscillator.type = 'square';
                    oscillator.frequency.setValueAtTime(880, ctx.currentTime);
                    oscillator.connect(ctx.destination);
                    oscillator.start();
                    oscillator.stop(ctx.currentTime + 0.3);
                    </script>
                    """, unsafe_allow_html=True)

                st.success(f"✅ Analysis complete — {len(enriched)} violation(s) found and logged")

                for v in enriched:
                    level = v["severity"].lower()
                    st.markdown(f"""
                    **{v['behavior_class']}**
                    <span class="{level}">{v['severity']}</span>
                    — at {v['timestamp']}s — {v['zone']}
                    """, unsafe_allow_html=True)
                    st.caption(v['description'])
            else:
                st.success("✅ No violations detected in this clip")

            # Rerun to update status indicator
            st.rerun()

        # Cleanup temp files
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(temp_policy_path):
            os.remove(temp_policy_path)
    else:
        st.info("⬆️ Upload both a policy document (PDF) and a video clip (.mp4) to begin analysis")

# ─── VIEW B: ALERT TIMELINE ───────────────────────────────────────
elif view == "🚨 Alert Timeline":
    st.header("🚨 Alert Timeline")

    # Filters for the timeline
    col1, col2 = st.columns([3, 1])
    with col2:
        show_all = st.checkbox("Show all severities", value=False)
    with col1:
        if show_all:
            timeline_sev = st.selectbox(
                "Filter by severity",
                ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                key="timeline_sev"
            )
        else:
            timeline_sev = None  # Only HIGH/CRITICAL shown by default

    violations = get_all_violations()

    if not show_all:
        violations = [v for v in violations if v["severity"] in ["HIGH", "CRITICAL"]]
    elif timeline_sev and timeline_sev != "All":
        violations = [v for v in violations if v["severity"] == timeline_sev]

    if violations:
        # Auto-refresh indicator
        st.caption(f"Showing {len(violations)} events — refreshes automatically every 5s")

        for v in violations:
            level = v["severity"].lower()
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{v['behavior_class']}**")
                    st.caption(v["event_description"])
                with c2:
                    st.markdown(f"<span class='{level}'>{v['severity']}</span>", unsafe_allow_html=True)
                    st.caption(v["clip_id"])
                with c3:
                    st.caption(v["timestamp"][:19])
                    st.caption(v["zone"])
                st.divider()

        # Auto-refresh
        time.sleep(5)
        st.rerun()
    else:
        if show_all:
            st.info("No events match the selected filter. Analyze some video clips first.")
        else:
            st.info("No HIGH or CRITICAL alerts yet. Analyze some video clips first.")

# ─── VIEW C: HISTORICAL LOG & EXPORT ──────────────────────────────
elif view == "📊 Historical Log":
    st.header("📊 Historical Compliance Log")

    # ── Filters: date range + severity + behavior class ───────────
    filter_row1 = st.columns(2)
    with filter_row1[0]:
        date_from = st.date_input(
            "From date",
            value=datetime.now().date() - timedelta(days=30),
            key="date_from"
        )
    with filter_row1[1]:
        date_to = st.date_input(
            "To date",
            value=datetime.now().date(),
            key="date_to"
        )

    filter_row2 = st.columns(2)
    with filter_row2[0]:
        sev_filter = st.selectbox(
            "Filter by severity",
            ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
        )
    with filter_row2[1]:
        behavior_filter = st.selectbox(
            "Filter by violation type",
            ["All",
             "Safe Walkway Violation",
             "Unauthorized Intervention",
             "Opened Panel Cover",
             "Carrying Overload with Forklift"]
        )

    # Fetch with all filters applied (including date range)
    violations = get_all_violations(
        severity_filter=sev_filter if sev_filter != "All" else None,
        behavior_filter=behavior_filter if behavior_filter != "All" else None,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None
    )

    if violations:
        df = pd.DataFrame(violations)

        # Color-code severity column
        def highlight_severity(val):
            colors = {
                "CRITICAL": "background-color: #7f1d1d; color: #fecaca",
                "HIGH": "background-color: #78350f; color: #fde68a",
                "MEDIUM": "background-color: #1e3a5f; color: #bfdbfe",
                "LOW": "background-color: #14532d; color: #bbf7d0"
            }
            return colors.get(val, "")

        # Show table
        display_cols = ["timestamp", "clip_id", "behavior_class", "severity", "zone", "escalation_action"]
        st.dataframe(
            df[display_cols].style.map(highlight_severity, subset=["severity"]),
            use_container_width=True,
            height=400
        )

        st.caption(f"Showing {len(violations)} records")

        # ── Export: generate CSV upfront, use a single download button ──
        # (Avoids the Streamlit nested-button bug where st.download_button
        #  inside st.button doesn't render properly)
        csv_path = export_to_csv()
        if csv_path:
            with open(csv_path, "r") as f:
                csv_data = f.read()
            st.download_button(
                label="📥 Export to CSV",
                data=csv_data,
                file_name="violations_export.csv",
                mime="text/csv"
            )
    else:
        st.info("No violations match the current filters.")