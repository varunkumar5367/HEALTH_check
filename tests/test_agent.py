import pytest
from app.ingest.loaders import DataLoader
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever
from app.agent.tools import ToolRegistry
from app.agent.loop import TriageAgentLoop

def test_agent_loop_sample_scenario():
    loader = DataLoader()
    df_alarms = loader.load_alarms()
    G_topo = loader.load_topology_graph()
    df_kpi = loader.load_kpis()
    
    correlator = AlarmCorrelator(topology_graph=G_topo, window_minutes=5)
    ranker = RootCauseRanker(topology_graph=G_topo)
    anomaly_checker = KPIAnomalyChecker(kpi_df=df_kpi)
    retriever = RAGRetriever()
    tools = ToolRegistry(loader=loader, anomaly_checker=anomaly_checker, retriever=retriever)
    
    agent = TriageAgentLoop(tool_registry=tools, ranker=ranker)
    
    # Filter alarms for Storm 1 (10:00 - 10:05)
    storm1_df = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T10:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T10:05:00Z")]
    incidents = correlator.correlate(storm1_df)
    assert len(incidents) >= 1
    
    result = agent.run_triage(incidents[0])
    
    # Verify agent loop result
    assert result["probable_root_node"] == "LINK-A"
    assert result["severity"] in ["CRITICAL", "HIGH"]
    assert len(result["reasoning_trace"]) <= 8  # MAX_STEPS guardrail enforced
    assert result["status"] == "TRIAGED"
    
    # Verify citations and ticket draft
    assert len(result["cited_next_checks"]) > 0
    assert result["cited_next_checks"][0]["citation"] != "not found"
    assert "draft_ticket" in result
    assert result["draft_ticket"]["ticket_id"].startswith("TICK-")

def test_agent_max_steps_guardrail():
    loader = DataLoader()
    G_topo = loader.load_topology_graph()
    df_kpi = loader.load_kpis()
    ranker = RootCauseRanker(topology_graph=G_topo)
    anomaly_checker = KPIAnomalyChecker(kpi_df=df_kpi)
    retriever = RAGRetriever()
    tools = ToolRegistry(loader=loader, anomaly_checker=anomaly_checker, retriever=retriever)
    
    # Set max_steps to 3 to force guardrail escalation
    agent = TriageAgentLoop(tool_registry=tools, ranker=ranker, max_steps=3)
    
    dummy_inc = {
        "id": "INC-TEST",
        "nodes_affected": ["CMG-01"],
        "alarms": [{"node": "CMG-01", "alarm_code": "CPU_HIGH", "node_type": "CMG", "severity": "CRITICAL", "type": "Hardware", "timestamp": "2026-10-08T12:00:00Z", "description": "test"}]
    }
    
    res = agent.run_triage(dummy_inc)
    assert res["status"] == "HANDOVER_ENGINEER_REVIEW"
