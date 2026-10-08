import pytest
from app.ingest.loaders import DataLoader
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker

def test_root_cause_ranking_sample_scenario():
    loader = DataLoader()
    df_alarms = loader.load_alarms()
    G_topo = loader.load_topology_graph()
    
    correlator = AlarmCorrelator(topology_graph=G_topo, window_minutes=5)
    ranker = RootCauseRanker(topology_graph=G_topo)
    
    # Filter alarms for Storm 1 (10:00 - 10:05)
    storm1_df = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T10:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T10:05:00Z")]
    incidents = correlator.correlate(storm1_df)
    
    assert len(incidents) >= 1
    inc = ranker.rank_incident(incidents[0])
    
    # Check sample scenario requirements:
    # Root cause: LINK-A (Physical Fiber Link Down)
    assert inc["probable_root_node"] == "LINK-A"
    assert "LINK_DOWN" in inc["probable_root_code"] or "LINK" in inc["probable_root"]
    
    # Severity should be HIGH or CRITICAL
    assert inc["severity"] in ["CRITICAL", "HIGH"]
    
    # Symptoms should contain CMG-02 / CMG-03 alarms
    assert len(inc["symptoms"]) > 0
    assert any("CMG-02" in s for s in inc["symptoms"])

def test_severity_rule_calc():
    loader = DataLoader()
    G_topo = loader.load_topology_graph()
    ranker = RootCauseRanker(topology_graph=G_topo)
    
    # >10 alarms and multiple nodes -> CRITICAL
    alarms = [{"severity": "CRITICAL", "type": "Transport"}] * 12
    nodes = ["LINK-A", "CMG-02", "CMG-03"]
    sev = ranker.calculate_severity(alarms, nodes)
    assert sev == "CRITICAL"
