import pytest
import pandas as pd
import networkx as nx
from app.ingest.loaders import DataLoader
from app.ingest.schemas import AlarmSchema

def test_data_loader_alarms():
    loader = DataLoader()
    df_alarms = loader.load_alarms()
    assert isinstance(df_alarms, pd.DataFrame)
    assert len(df_alarms) > 100
    expected_cols = ["alarm_id", "timestamp", "node", "node_type", "alarm_code", "alarm_name", "severity", "type", "description", "status"]
    for col in expected_cols:
        assert col in df_alarms.columns

def test_alarm_schema_validation():
    sample_alarm = {
        "alarm_id": "ALM-TEST-001",
        "timestamp": "2026-10-08T10:00:00Z",
        "node": "LINK-A",
        "node_type": "Transport",
        "alarm_code": "LINK_DOWN",
        "alarm_name": "Link Down Test",
        "severity": "CRITICAL",
        "type": "Transport",
        "description": "Test alarm description",
        "status": "ACTIVE"
    }
    alarm_obj = AlarmSchema(**sample_alarm)
    assert alarm_obj.node == "LINK-A"
    assert alarm_obj.severity == "CRITICAL"

def test_data_loader_topology():
    loader = DataLoader()
    G = loader.load_topology_graph()
    assert isinstance(G, nx.DiGraph)
    assert "LINK-A" in G.nodes
    assert "CMG-02" in G.nodes
    assert G.has_edge("LINK-A", "CMG-02") or G.has_edge("CMG-02", "LINK-A")

def test_data_loader_kpi():
    loader = DataLoader()
    df_kpi = loader.load_kpis()
    assert isinstance(df_kpi, pd.DataFrame)
    assert len(df_kpi) > 500
    assert "kpi_name" in df_kpi.columns
    assert "value" in df_kpi.columns

def test_data_loader_runbooks_and_incidents():
    loader = DataLoader()
    runbooks = loader.load_runbooks()
    assert len(runbooks) >= 10
    
    past_incidents = loader.load_past_incidents()
    assert len(past_incidents) >= 10
