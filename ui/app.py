import sys
from pathlib import Path

# Add project root directory to sys.path so app module is always resolvable
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import requests
import networkx as nx
import json

from app.config import settings
from app.ingest.loaders import DataLoader
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever
from app.agent.tools import ToolRegistry
from app.agent.loop import TriageAgentLoop

st.set_page_config(
    page_title="Network Triage Agent - PS06",
    page_icon="📡",
    layout="wide"
)

st.title("📡 Network Health-Check and Alarm Triage Agent")
st.markdown("*Autonomous Read-Only Alarm Storm Correlation, Root Cause Analysis & Runbook-Cited Triage Summary*")

# Load Backend Singletons
@st.cache_resource
def init_system():
    loader = DataLoader()
    df_alarms = loader.load_alarms()
    G_topo = loader.load_topology_graph()
    df_kpi = loader.load_kpis()
    
    correlator = AlarmCorrelator(topology_graph=G_topo)
    ranker = RootCauseRanker(topology_graph=G_topo)
    anomaly_checker = KPIAnomalyChecker(kpi_df=df_kpi)
    retriever = RAGRetriever()
    tools = ToolRegistry(loader=loader, anomaly_checker=anomaly_checker, retriever=retriever)
    agent = TriageAgentLoop(tool_registry=tools, ranker=ranker)
    
    return loader, df_alarms, G_topo, df_kpi, correlator, ranker, anomaly_checker, retriever, tools, agent

loader, df_alarms, G_topo, df_kpi, correlator, ranker, anomaly_checker, retriever, tools, agent = init_system()

# Sidebar Data & Preset Selection
st.sidebar.header("🕹️ Scenario & Dataset Controls")
scenario = st.sidebar.selectbox(
    "Select Incident Storm Scenario",
    [
        "Storm 1: Sample Scenario (LINK-A Fiber Down -> BGP Down -> CMG Degradation)",
        "Storm 2: CMG-01 CPU/Memory Spike -> GTP Path Failures",
        "Storm 3: CMG-03 PFCP Heartbeat Fail -> UPF-02 Bearer Drops",
        "Storm 4: LINK-B Fiber Break -> UPF-01/UPF-02 Packet Loss",
        "All Synthetic Alarms (~500 Alarms)"
    ]
)

# Filter alarms based on selection
if "Storm 1" in scenario:
    filtered_alarms = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T10:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T10:05:00Z")]
elif "Storm 2" in scenario:
    filtered_alarms = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T12:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T12:05:00Z")]
elif "Storm 3" in scenario:
    filtered_alarms = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T14:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T14:05:00Z")]
elif "Storm 4" in scenario:
    filtered_alarms = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T16:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T16:05:00Z")]
else:
    filtered_alarms = df_alarms

# Correlate into Incidents
incidents = correlator.correlate(filtered_alarms)

# Metric Summary Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Raw Alarms Ingested", len(filtered_alarms))
col2.metric("Correlated Incidents", len(incidents))
col3.metric("Topology Nodes Monitored", len(G_topo.nodes))
col4.metric("Agent Mode", "READ-ONLY (Human Gated)")

st.divider()

if not incidents:
    st.info("No active incident storms found in selected window.")
else:
    inc_titles = [f"{inc['id']} - {inc['title']} ({inc['total_alarms']} alarms)" for inc in incidents]
    selected_inc_idx = st.selectbox("Select Correlated Incident to Triage:", range(len(inc_titles)), format_func=lambda i: inc_titles[i])
    
    target_inc = incidents[selected_inc_idx]
    
    # Run Agent Loop
    triage_res = agent.run_triage(target_inc)
    
    # Overview Banner
    sev_color = "🔴" if triage_res["severity"] == "CRITICAL" else ("🟠" if triage_res["severity"] == "HIGH" else "🟡")
    st.subheader(f"{sev_color} Triage Summary: {target_inc['id']}")
    
    b1, b2, b3, b4 = st.columns(4)
    b1.markdown(f"**Probable Root Cause:**\n### `{triage_res['probable_root']}`")
    b2.markdown(f"**Assigned Severity:**\n### `{triage_res['severity']}`")
    b3.markdown(f"**Confidence Score:**\n### `{triage_res['confidence_score']*100:.1f}%`")
    b4.markdown(f"**Triage Status:**\n### `{triage_res['status']}`")

    st.markdown(f"**Grouping Rationale:** {triage_res['grouping_rationale']}")

    # Tabs for Triage Views
    tab_overview, tab_topology, tab_kpi, tab_trace, tab_checks, tab_ticket = st.tabs([
        "📊 Alarms & Symptoms", "🌐 Topology Graph", "📈 KPI Baseline & Anomalies",
        "🧠 Agent Reasoning Trace", "📚 Cited Runbook Checks", "🎫 Draft Ticket & Action"
    ])

    with tab_overview:
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("### 🚨 Probable Root Cause Alarm")
            st.error(f"**Node:** {triage_res['probable_root_node']}\n\n**Code:** `{triage_res['probable_root_code']}`")
            st.json({
                "node": triage_res["probable_root_node"],
                "code": triage_res["probable_root_code"],
                "explanation": target_inc.get("ranking_explanation", "Highest onset & topology score.")
            })
            
        with c_right:
            st.markdown(f"### 🩺 Grouped Symptoms ({len(triage_res['symptoms'])})")
            st.dataframe(pd.DataFrame({"Grouped Symptom Alarms": triage_res["symptoms"]}), use_container_width=True)

    with tab_topology:
        st.markdown("### 🌐 Affected Network Topology")
        st.info("Topological dependency map highlighting the Probable Root node.")
        
        edges_data = []
        root_node = triage_res["probable_root_node"]
        for u, v, data in G_topo.edges(data=True):
            status = "🔴 ROOT NODE" if u == root_node or v == root_node else "🟢 NORMAL"
            edges_data.append({"Source Node": u, "Target Node": v, "Link Type": data.get("link_type", "Transport"), "Dependency Status": status})
        st.table(pd.DataFrame(edges_data))

    with tab_kpi:
        st.markdown("### 📈 KPI Baseline & Directional Anomaly Analysis")
        node_select = st.selectbox("Select Node for KPI Check:", target_inc["nodes_affected"])
        kpi_select = st.selectbox("Select Metric:", ["bgp_session_state", "cpu_utilization", "memory_utilization", "throughput_gbps", "packet_loss_pct", "active_bearers"])
        
        df_node_kpi = anomaly_checker.get_kpi(node_select, kpi_select, window_minutes=60)
        if not df_node_kpi.empty:
            st.line_chart(df_node_kpi.set_index("timestamp")["value"])
            anomalies = anomaly_checker.check_node_anomalies(node_select)
            if anomalies:
                st.warning(f"Detected {len(anomalies)} KPI anomalies on {node_select}:")
                st.json(anomalies)
            else:
                st.success(f"No anomalous Z-score deviations detected on {node_select} for metric {kpi_select}.")

    with tab_trace:
        st.markdown("### 🧠 Visible Reasoning Trace (Observe -> Hypothesise -> Act -> Evaluate -> Conclude)")
        for step in triage_res["reasoning_trace"]:
            with st.expander(f"Step {step['step']}: [{step['action']}] via tool `{step['tool']}`"):
                st.markdown(f"**Input:** `{step['input']}`")
                st.markdown(f"**Output:** `{step['output']}`")
                st.markdown(f"**Conclusion:** *{step['conclusion']}*")

    with tab_checks:
        st.markdown("### 📚 Runbook-Cited Next Checks & Past Incidents")
        col_chk, col_past = st.columns(2)
        with col_chk:
            st.markdown("#### 📖 Cited Next Checks (Mandatory Runbook Section Citations)")
            for chk in triage_res["cited_next_checks"]:
                st.markdown(f"📌 **Citation:** `{chk.get('citation')}`")
                st.caption(chk.get("content", "")[:300])
                st.divider()
                
        with col_past:
            st.markdown("#### 📜 Similar Past Incidents")
            for past in triage_res["similar_past_incidents"]:
                st.markdown(f"🏷️ **Incident ID:** `{past.get('id')}` (Similarity: `{past.get('similarity')}`)")
                st.text(past.get("content", "")[:250])
                st.divider()

    with tab_ticket:
        st.markdown("### 🎫 Draft Ticket Preview & Human-in-the-Loop Action Gate")
        draft = triage_res["draft_ticket"]
        
        st.text_input("Ticket Title", value=draft["title"])
        st.text_area("Ticket Description", value=draft["description"], height=200)
        
        st.warning("⚠️ **HARD RULE**: The Triage Agent is strictly READ-ONLY. Actions require human NOC engineer confirmation.")
        
        confirm = st.checkbox("I validate and confirm these triage findings as a NOC/SNOC Engineer.")
        
        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("📢 Send Teams / Email Notification", disabled=not confirm):
                st.success("Notification delivered to NOC Teams Channel! Payload stored in notification registry.")
        with act_col2:
            if st.button("🎫 Create Ticket in ITSM", disabled=not confirm):
                st.success(f"Ticket {draft['ticket_id']} successfully submitted to ITSM!")
