import pytest
from app.ingest.loaders import DataLoader
from app.correlation.root_cause import RootCauseRanker
from app.agent.tools import ToolRegistry
from app.agent.loop import TriageAgentLoop
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever
from app.notify.mailer import EmailDispatcher
from app.monitor.connection import CloudNodeConnection
from app.monitor.daemon import CloudNodeMonitorDaemon

def test_cloud_node_connection():
    conn = CloudNodeConnection("CMG-01", host="10.95.176.101")
    assert conn.connect()
    telemetry = conn.poll_telemetry()
    assert telemetry["node_id"] == "CMG-01"
    assert "cpu_utilization" in telemetry

def test_cloud_node_monitor_fault_simulation():
    loader = DataLoader()
    G_topo = loader.load_topology_graph()
    df_kpi = loader.load_kpis()
    ranker = RootCauseRanker(topology_graph=G_topo)
    anomaly_checker = KPIAnomalyChecker(kpi_df=df_kpi)
    retriever = RAGRetriever()
    tools = ToolRegistry(loader=loader, anomaly_checker=anomaly_checker, retriever=retriever)
    agent = TriageAgentLoop(tool_registry=tools, ranker=ranker)
    mailer = EmailDispatcher(use_mock=True)

    daemon = CloudNodeMonitorDaemon(agent_loop=agent, mailer=mailer)
    
    # Simulate node parameter fault
    fault_res = daemon.simulate_node_fault("LINK-A", "LINK_DOWN", "Physical Fiber Link Down", recipient_email="noc-test@telco.com")
    
    assert fault_res["status"] == "FAULT_DETECTED"
    assert fault_res["triage_result"]["probable_root_node"] == "LINK-A"
    assert fault_res["email_dispatch"]["recipient"] == "noc-test@telco.com"
    assert len(daemon.event_log) > 0
