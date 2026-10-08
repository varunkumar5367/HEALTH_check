import pytest
import pandas as pd
from app.ingest.loaders import DataLoader
from app.correlation.engine import AlarmCorrelator

def test_alarm_correlator_sample_scenario():
    loader = DataLoader()
    df_alarms = loader.load_alarms()
    G_topo = loader.load_topology_graph()
    
    correlator = AlarmCorrelator(topology_graph=G_topo, window_minutes=5)
    
    # Filter alarms for Storm 1 (10:00 - 10:05)
    storm1_df = df_alarms[(df_alarms["timestamp"] >= "2026-10-08T10:00:00Z") & (df_alarms["timestamp"] <= "2026-10-08T10:05:00Z")]
    assert len(storm1_df) >= 30
    
    incidents = correlator.correlate(storm1_df)
    
    # Should group into 1 primary incident storm
    assert len(incidents) >= 1
    sample_inc = incidents[0]
    
    assert "LINK-A" in sample_inc["nodes_affected"]
    assert "CMG-02" in sample_inc["nodes_affected"]
    assert len(sample_inc["alarms"]) >= 30
    assert "Grouped" in sample_inc["grouping_rationale"]

def test_alarm_correlator_full_dataset():
    loader = DataLoader()
    df_alarms = loader.load_alarms()
    G_topo = loader.load_topology_graph()
    
    correlator = AlarmCorrelator(topology_graph=G_topo, window_minutes=5)
    incidents = correlator.correlate(df_alarms)
    
    # Should produce discrete incidents including the 4 planted storms
    assert len(incidents) >= 4
    storm_nodes = [set(inc["nodes_affected"]) for inc in incidents]
    
    # Check that LINK-A and CMG-02 storm is captured
    found_storm1 = any("LINK-A" in nodes and "CMG-02" in nodes for nodes in storm_nodes)
    assert found_storm1
