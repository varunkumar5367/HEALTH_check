import sys
import os
from pathlib import Path

# Add project root directory to sys.path so app module is always resolvable at top priority
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) in sys.path:
    sys.path.remove(str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import requests
import networkx as nx
import json
from datetime import datetime

from app.config import settings
from app.ingest.loaders import DataLoader
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever
from app.agent.tools import ToolRegistry
from app.agent.loop import TriageAgentLoop
from app.notify.mailer import EmailDispatcher
from app.notify.email_formatter import EmailRCAFormatter
from app.monitor.daemon import CloudNodeMonitorDaemon

st.set_page_config(
    page_title="Network Triage Agent - PS06",
    page_icon="📡",
    layout="wide"
)

st.title("📡 Network Health-Check, Cloud Monitor & Alarm Triage Agent")
st.markdown("*Autonomous Cloud Node Monitoring, Error Detection, Root Cause Analysis & Cited Solution Email Dispatch*")

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
    mailer = EmailDispatcher()
    monitor_daemon = CloudNodeMonitorDaemon(agent_loop=agent, mailer=mailer)
    
    return loader, df_alarms, G_topo, df_kpi, correlator, ranker, anomaly_checker, retriever, tools, agent, mailer, monitor_daemon

loader, df_alarms, G_topo, df_kpi, correlator, ranker, anomaly_checker, retriever, tools, agent, mailer, monitor_daemon = init_system()

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

# Email Settings in Sidebar
st.sidebar.divider()
st.sidebar.header("📧 Email Alert Settings")
recipient_email = st.sidebar.text_input("Engineer Email Recipient", value=settings.ALERT_EMAIL_RECIPIENT)
smtp_mode = st.sidebar.radio("Email Dispatch Mode", ["Live SMTP Relay", "Sandbox Outbox (Mock)"], index=0)

if smtp_mode == "Live SMTP Relay":
    mailer.use_mock = False
    mailer.smtp_user = settings.SMTP_USER
    mailer.smtp_password = settings.SMTP_PASSWORD
    st.sidebar.success(f"✅ Live Gmail SMTP Active (`{settings.SMTP_USER}`)")
else:
    mailer.use_mock = True

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
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Raw Alarms Ingested", len(filtered_alarms))
col2.metric("Correlated Incidents", len(incidents))
col3.metric("Cloud Nodes Monitored", len(G_topo.nodes))
col4.metric("Live Daemon", "ACTIVE" if monitor_daemon.running else "STOPPED")
col5.metric("Outbox Emails Sent", len(mailer.outbox_history))

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
    tab_cloud, tab_overview, tab_topology, tab_kpi, tab_trace, tab_checks, tab_ticket = st.tabs([
        "☁️ Cloud Monitor & Email Alert", "📊 Alarms & Symptoms", "🌐 Topology Graph",
        "📈 KPI Baseline & Anomalies", "🧠 Agent Reasoning Trace", "📚 Cited Runbook Checks", "🎫 Draft Ticket & Action"
    ])

    with tab_cloud:
        st.markdown("### ☁️ Continuous Cloud Node Monitoring & Automated Email RCA Dispatch")
        st.info("The agent continuously polls connected Cloud Nodes/Linux VMs. Upon parameter fluctuation or KPI failure, it auto-detects errors, executes Root Cause Analysis (RCA), and dispatches cited solution emails directly to the designated NOC engineer.")

        # Top Columns: Node Input Form & Daemon Control
        col_add, col_ctrl = st.columns(2)

        with col_add:
            st.markdown("#### ➕ Connect New Cloud Node / Linux VM")
            with st.form("add_node_form"):
                new_node_id = st.text_input("Node ID / Hostname", value="CMG-04", help="Unique node identifier (e.g. CMG-04, UPF-03)")
                c1, c2, c3 = st.columns(3)
                new_host = c1.text_input("IP Address / Host", value="10.95.176.104")
                new_port = c2.number_input("SSH/REST Port", value=22, min_value=1, max_value=65535)
                new_type = c3.selectbox("Node Type", ["CMG", "UPF", "Transport", "Router"])
                
                submitted = st.form_submit_button("🔌 Connect & Add to Continuous Monitor")
                if submitted:
                    conn = monitor_daemon.add_node(new_node_id, host=new_host, port=int(new_port), node_type=new_type)
                    st.success(f"Connected node `{new_node_id}` ({new_host}:{new_port}) to continuous monitoring list!")

        with col_ctrl:
            st.markdown("#### ⚙️ Continuous Monitoring Daemon & Email Settings")
            daemon_active = st.toggle("Enable Continuous Cloud Monitoring Daemon", value=monitor_daemon.running)
            if daemon_active != monitor_daemon.running:
                if daemon_active:
                    monitor_daemon.start()
                    st.success("Cloud Monitoring Daemon STARTED!")
                else:
                    monitor_daemon.stop()
                    st.warning("Cloud Monitoring Daemon STOPPED.")
            
            st.markdown(f"**Daemon Status:** `{'ACTIVE' if monitor_daemon.running else 'STOPPED'}` | **Interval:** `{monitor_daemon.interval_seconds}s`")
            st.markdown(f"**Target Recipient:** `{recipient_email}`")
            st.markdown(f"**Active Dispatch Mode:** `{'Sandbox Outbox (Mock)' if mailer.use_mock else 'Live SMTP Relay'}`")

        st.divider()

        # Section: Live Telemetry Parameters Table
        st.markdown("#### 🖥️ Monitored Cloud Nodes & Live Telemetry Parameters")
        telemetry_records = []
        for conn in monitor_daemon.nodes:
            telemetry_records.append(conn.poll_telemetry())
        
        df_telemetry = pd.DataFrame(telemetry_records)
        st.dataframe(
            df_telemetry[["node_id", "host", "cpu_utilization", "memory_utilization", "bgp_session_state", "throughput_gbps", "packet_loss_pct", "active_bearers", "status", "timestamp"]],
            use_container_width=True
        )

        st.divider()

        # Section: Fault Simulation & Automated Email Trigger
        st.markdown("#### ⚡ Real-time Cloud Error Detection & Email Dispatch Trigger")
        st.markdown("Simulate an unexpected parameter fluctuation on any connected node to test automatic error detection, AI RCA generation, and email dispatch:")
        
        sim_col1, sim_col2, sim_col3 = st.columns([2, 2, 3])
        with sim_col1:
            all_node_ids = [conn.node_id for conn in monitor_daemon.nodes]
            test_node = st.selectbox("Target Monitored Node", all_node_ids)
        with sim_col2:
            test_code = st.selectbox("Simulated Parameter Fault", ["LINK_DOWN", "CPU_HIGH", "BGP_PEER_DOWN", "PFCP_HEARTBEAT_FAIL", "PACKET_LOSS_HIGH"])
        with sim_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            trigger_btn = st.button("🚨 Simulate Error & Dispatch RCA Email", use_container_width=True)

        if trigger_btn:
            fault_res = monitor_daemon.simulate_node_fault(
                node_id=test_node,
                alarm_code=test_code,
                alarm_name=test_code.replace("_", " ").title(),
                recipient_email=recipient_email
            )
            st.success(f"⚠️ Error detected on cloud node `{test_node}`! Triage completed and Solution Email dispatched to `{recipient_email}`.")
            with st.expander("📄 View Dispatched Email Payload & Dispatch Audit Log", expanded=True):
                st.json(fault_res["email_dispatch"])

        st.divider()
        st.markdown("### 📧 Outbox History & Generated Solution Email Preview")
        if mailer.outbox_history:
            st.dataframe(pd.DataFrame(mailer.outbox_history), use_container_width=True)
            
            # Preview latest email
            latest_email = mailer.outbox_history[-1]
            st.markdown(f"#### ✉️ Preview Latest Dispatched Email (`{latest_email['dispatch_id']}` -> `{latest_email['recipient']}`)")
            formatted_email = EmailRCAFormatter.format_rca_email(triage_res, recipient_email)
            st.components.v1.html(formatted_email["html"], height=500, scrolling=True)
        else:
            st.caption("No emails dispatched in this session yet. Click the button above to simulate an error and send a solution email!")

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
        
        act_col1, act_col2, act_col3 = st.columns(3)
        with act_col1:
            if st.button("📢 Send Teams Notification", disabled=not confirm):
                st.success("Notification delivered to NOC Teams Channel! Payload stored in notification registry.")
        with act_col2:
            if st.button("📧 Dispatch RCA Solution Email", disabled=not confirm):
                mail_res = mailer.send_rca_email(triage_res, recipient=recipient_email)
                st.success(f"RCA Solution Email successfully dispatched to {recipient_email}!")
                st.json(mail_res)
        with act_col3:
            if st.button("🎫 Create Ticket in ITSM", disabled=not confirm):
                st.success(f"Ticket {draft['ticket_id']} successfully submitted to ITSM!")
