import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import sys
import time

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

# ─── VIEW A: LIVE FEED ────────────────────────────────────────────
if view == "📹 Live Feed Monitor":
    st.header("📹 Live Feed Monitor")

    uploaded = st.file_uploader(
        "Upload a video clip to analyze",
        type=["mp4", "avi", "mov"]
    )

    if uploaded:
        # Save uploaded file temporarily
        temp_path = f"data/temp_{uploaded.name}"
        os.makedirs("data", exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(uploaded.read())

        st.video(temp_path)

        if st.button("🔍 Analyze for Violations", type="primary"):
            with st.spinner("Running ResNet50 detection on frames..."):
                from src.detection import classify_video, load_model
                model, device = load_model()
                v = classify_video(temp_path, model, device)
                violations = [v] if v else []

                # Enrich with severity
                enriched = [enrich_violation(v) for v in violations]

                # Save to DB and Trigger Escalation
                from src.escalation import trigger_escalation
                for v in enriched:
                    save_violation(v)
                    trigger_escalation(v)

            if enriched:
                # Check if any are HIGH/CRITICAL for alert banner
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

        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    else:
        st.info("⬆️ Upload an .mp4 clip from the Kaggle dataset to begin analysis")

# ─── VIEW B: ALERT TIMELINE ───────────────────────────────────────
elif view == "🚨 Alert Timeline":
    st.header("🚨 Alert Timeline")

    # Only show HIGH and CRITICAL
    col1, col2 = st.columns([3, 1])
    with col2:
        show_all = st.checkbox("Show all severities", value=False)

    violations = get_all_violations()

    if not show_all:
        violations = [v for v in violations if v["severity"] in ["HIGH", "CRITICAL"]]

    if violations:
        # Auto-refresh every 5 seconds
        st.caption(f"Showing {len(violations)} events — refreshes automatically")

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
        st.info("No HIGH or CRITICAL alerts yet. Analyze some video clips first.")

# ─── VIEW C: HISTORICAL LOG ───────────────────────────────────────
elif view == "📊 Historical Log":
    st.header("📊 Historical Compliance Log")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        sev_filter = st.selectbox(
            "Filter by severity",
            ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
        )
    with col2:
        behavior_filter = st.selectbox(
            "Filter by violation type",
            ["All",
             "Safe Walkway Violation",
             "Unauthorized Intervention",
             "Opened Panel Cover",
             "Carrying Overload with Forklift"]
        )

    violations = get_all_violations(
        severity_filter=sev_filter if sev_filter != "All" else None,
        behavior_filter=behavior_filter if behavior_filter != "All" else None
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
            df[display_cols].style.applymap(highlight_severity, subset=["severity"]),
            use_container_width=True,
            height=400
        )

        st.caption(f"Showing {len(violations)} records")

        # Export button
        if st.button("📥 Export to CSV"):
            csv_path = export_to_csv()
            if csv_path:
                with open(csv_path, "r") as f:
                    st.download_button(
                        label="⬇️ Download violations.csv",
                        data=f.read(),
                        file_name="violations_export.csv",
                        mime="text/csv"
                    )
    else:
        st.info("No violations match the current filters.")