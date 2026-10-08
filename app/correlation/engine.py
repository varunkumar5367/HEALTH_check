import pandas as pd
import networkx as nx
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from app.config import settings
from app.ingest.loaders import DataLoader

class AlarmCorrelator:
    """
    Correlates raw alarms into discrete Incident objects using temporal sliding windows,
    topology proximity (shortest path distance), and alarm type dependencies.
    """
    def __init__(self, topology_graph: nx.DiGraph, window_minutes: int = settings.TIME_WINDOW_MINUTES, max_hops: int = settings.TOPOLOGY_MAX_HOPS):
        self.topology_graph = topology_graph
        self.window_minutes = window_minutes
        self.max_hops = max_hops

    def _are_nodes_connected(self, node1: str, node2: str) -> bool:
        if node1 == node2:
            return True
        if node1 not in self.topology_graph or node2 not in self.topology_graph:
            return False
        try:
            distance = nx.shortest_path_length(self.topology_graph, source=node1, target=node2)
            return distance <= self.max_hops
        except nx.NetworkXNoPath:
            return False

    def correlate(self, alarms_df: pd.DataFrame) -> List[Dict[str, Any]]:
        if alarms_df.empty:
            return []

        # Ensure timestamp is datetime
        df = alarms_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.sort_values(by="timestamp", inplace=True)

        alarms_list = df.to_dict("records")
        num_alarms = len(alarms_list)

        # 1. Temporal Clustering
        temporal_clusters = []
        current_cluster = []

        for alarm in alarms_list:
            if not current_cluster:
                current_cluster.append(alarm)
            else:
                last_time = current_cluster[-1]["timestamp"]
                curr_time = alarm["timestamp"]
                # Sliding window check: time diff from previous alarm in cluster
                if (curr_time - last_time) <= timedelta(minutes=self.window_minutes):
                    current_cluster.append(alarm)
                else:
                    temporal_clusters.append(current_cluster)
                    current_cluster = [alarm]
        if current_cluster:
            temporal_clusters.append(current_cluster)

        # 2. Topology Proximity & Alarm Type Graph Partitioning
        incidents = []
        inc_counter = 1

        for cluster in temporal_clusters:
            # Build graph for this temporal cluster
            corr_graph = nx.Graph()
            for i, alm in enumerate(cluster):
                corr_graph.add_node(i)

            for i in range(len(cluster)):
                for j in range(i + 1, len(cluster)):
                    node_i = cluster[i]["node"]
                    node_j = cluster[j]["node"]

                    # Topology check
                    if self._are_nodes_connected(node_i, node_j):
                        # Add edge between alarms
                        corr_graph.add_edge(i, j)

            # Extract connected components
            components = list(nx.connected_components(corr_graph))
            for comp in components:
                comp_alarms = [cluster[idx] for idx in comp]
                comp_alarms.sort(key=lambda x: x["timestamp"])

                nodes_affected = list(set(a["node"] for a in comp_alarms))
                start_time = comp_alarms[0]["timestamp"]
                end_time = comp_alarms[-1]["timestamp"]
                
                # Format ISO strings
                start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(start_time, datetime) else str(start_time)
                end_iso = end_time.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(end_time, datetime) else str(end_time)

                inc_id = f"INC-20261008-{inc_counter:03d}"
                inc_counter += 1

                # Generate clear grouping rationale
                alarm_types = list(set(a.get("type", "General") for a in comp_alarms))
                rationale = (
                    f"Grouped {len(comp_alarms)} alarms arriving within a {self.window_minutes}-minute sliding window "
                    f"({start_iso} to {end_iso}) across topolocially linked nodes [{', '.join(nodes_affected)}] "
                    f"covering categories: {', '.join(alarm_types)}."
                )

                incidents.append({
                    "id": inc_id,
                    "title": f"Incident on {', '.join(nodes_affected)} ({len(comp_alarms)} alarms)",
                    "start_time": start_iso,
                    "end_time": end_iso,
                    "nodes_affected": nodes_affected,
                    "total_alarms": len(comp_alarms),
                    "alarms": comp_alarms,
                    "grouping_rationale": rationale
                })

        return incidents
