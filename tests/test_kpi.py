import pytest
import pandas as pd
from app.ingest.loaders import DataLoader
from app.kpi.anomaly import KPIAnomalyChecker

def test_kpi_anomaly_checker():
    loader = DataLoader()
    df_kpi = loader.load_kpis()
    checker = KPIAnomalyChecker(kpi_df=df_kpi)
    
    # Test get_kpi
    cmg02_cpu = checker.get_kpi(node="CMG-02", kpi_name="cpu_utilization", window_minutes=60)
    assert not cmg02_cpu.empty
    
    # Test Storm 1 BGP session state anomaly on CMG-02 at 10:05
    anomalies_storm1 = checker.check_node_anomalies(node="CMG-02", timestamp_str="2026-10-08T10:05:00Z")
    assert len(anomalies_storm1) > 0
    bgp_anom = [a for a in anomalies_storm1 if a["kpi_name"] == "bgp_session_state"]
    assert len(bgp_anom) > 0
    assert bgp_anom[0]["direction"] == "DOWN_ANOMALY"

def test_kpi_cpu_spike_anomaly():
    loader = DataLoader()
    df_kpi = loader.load_kpis()
    checker = KPIAnomalyChecker(kpi_df=df_kpi)
    
    # Test Storm 2 CPU spike anomaly on CMG-01 at 12:05
    anomalies_storm2 = checker.check_node_anomalies(node="CMG-01", timestamp_str="2026-10-08T12:05:00Z")
    cpu_anom = [a for a in anomalies_storm2 if a["kpi_name"] == "cpu_utilization"]
    assert len(cpu_anom) > 0
    assert cpu_anom[0]["z_score"] > 2.0
