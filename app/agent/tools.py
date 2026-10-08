import pandas as pd
import networkx as nx
from typing import Dict, Any, List

from app.ingest.loaders import DataLoader
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever

class ToolRegistry:
    """
    Read-only simulated device and diagnostic tools exposed to the Agent and REST API.
    """
    def __init__(self, loader: DataLoader, anomaly_checker: KPIAnomalyChecker, retriever: RAGRetriever):
        self.loader = loader
        self.topology_graph = loader.load_topology_graph()
        self.anomaly_checker = anomaly_checker
        self.retriever = retriever

    def ping(self, node: str) -> Dict[str, Any]:
        """Simulates ICMP ping to a network node."""
        if node not in self.topology_graph.nodes:
            return {"node": node, "status": "UNKNOWN", "latency_ms": None, "packet_loss_pct": 100.0}
            
        # Check node state
        if node in ["LINK-A", "LINK-B"]:
            return {"node": node, "status": "UNREACHABLE", "latency_ms": 0.0, "packet_loss_pct": 100.0, "details": "Physical optical link down"}
            
        return {"node": node, "status": "REACHABLE", "latency_ms": 0.45, "packet_loss_pct": 0.0, "details": "ICMP reply received 5/5"}

    def get_kpi(self, node: str, kpi: str, window_minutes: int = 15) -> Dict[str, Any]:
        """Queries recent KPI timeseries and anomaly summary for node."""
        df_kpi = self.anomaly_checker.get_kpi(node, kpi, window_minutes)
        anomalies = self.anomaly_checker.check_node_anomalies(node)
        anom_match = [a for a in anomalies if a["kpi_name"] == kpi]
        
        recent_vals = df_kpi["value"].tolist() if not df_kpi.empty else []
        return {
            "node": node,
            "kpi_name": kpi,
            "window_minutes": window_minutes,
            "recent_values": recent_vals[-5:],
            "has_anomaly": len(anom_match) > 0,
            "anomaly_details": anom_match[0] if anom_match else None
        }

    def show_status(self, node: str) -> Dict[str, Any]:
        """Shows simulated operational status of a node."""
        if node.startswith("LINK"):
            return {
                "node": node,
                "type": "Transport",
                "admin_status": "UP",
                "oper_status": "DOWN",
                "duplex": "Full",
                "alarms_active": ["LINK_DOWN"]
            }
        elif node.startswith("CMG"):
            return {
                "node": node,
                "type": "CMG",
                "cpm_status": "ACTIVE",
                "active_bgp_peers": 3 if node != "CMG-02" else 0,
                "cp_isa_status": "NORMAL",
                "active_sessions": 485000
            }
        elif node.startswith("UPF"):
            return {
                "node": node,
                "type": "UPF",
                "user_plane_status": "UP",
                "pfcp_association": "UP",
                "throughput_gbps": 95.4
            }
        return {"node": node, "status": "UNKNOWN"}

    def topology_neighbors(self, node: str) -> Dict[str, Any]:
        """Returns direct topological neighbors of node."""
        if node not in self.topology_graph:
            return {"node": node, "neighbors": []}
        neighbors = list(self.topology_graph.neighbors(node))
        return {"node": node, "neighbors": neighbors}

    def search_runbook(self, query: str, node_type: str = "") -> List[Dict[str, str]]:
        """Searches operational runbooks for cited next checks."""
        return self.retriever.get_next_checks(alarm_name=query, alarm_code="", node_type=node_type)

    def search_past_incidents(self, query: str) -> List[Dict[str, Any]]:
        """Searches past incidents for historical matches."""
        return self.retriever.get_similar_incidents(query)
