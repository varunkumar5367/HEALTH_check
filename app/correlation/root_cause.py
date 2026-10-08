import networkx as nx
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime

class RootCauseRanker:
    """
    Ranks candidate alarms/nodes within an incident to identify the Probable Root Cause.
    
    Scoring Criteria (Max 100 points):
    1. Earliest Onset (30 pts): Earliest alarm timestamp in the incident storm.
    2. Topology Upstream Position (25 pts): Upstream core node / transport edge with topological reach to downstream nodes.
    3. Alarm Type Causality (25 pts): 
       - Transport / Link Down (25 pts)
       - Hardware / Control Plane CPU/Memory Exhaustion (22 pts)
       - Protocol / BGP / PFCP session down (18 pts)
       - Service / Bearer / Session drops (10 pts)
    4. Symptoms Explained (10 pts): Number of downstream node symptoms explained.
    5. KPI Anomaly Support (10 pts): Empirical supporting KPI anomaly.
    """
    def __init__(self, topology_graph: nx.DiGraph):
        self.topology_graph = topology_graph

    def calculate_severity(self, alarms: List[Dict[str, Any]], nodes: List[str]) -> str:
        num_alarms = len(alarms)
        num_nodes = len(nodes)
        severities = [a.get("severity", "MINOR") for a in alarms]
        
        has_critical = "CRITICAL" in severities
        has_major = "MAJOR" in severities
        
        if num_alarms > 10 or num_nodes > 2 or (has_critical and "Transport" in [a.get("type") for a in alarms]):
            return "CRITICAL"
        elif num_alarms > 5 or num_nodes > 1 or has_critical or has_major:
            return "HIGH"
        elif num_alarms >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def rank_incident(self, incident: Dict[str, Any], kpi_anomalies: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        alarms = incident.get("alarms", [])
        if not alarms:
            return incident

        df_inc = pd.DataFrame(alarms)
        df_inc["timestamp"] = pd.to_datetime(df_inc["timestamp"])
        df_inc.sort_values(by="timestamp", inplace=True)

        earliest_time = df_inc.iloc[0]["timestamp"]
        
        candidates = {}
        for idx, row in df_inc.iterrows():
            node = row.get("node", "UNKNOWN")
            alarm_code = row.get("alarm_code", "UNKNOWN")
            key = f"{node}::{alarm_code}"
            
            if key not in candidates:
                candidates[key] = {
                    "node": node,
                    "node_type": row.get("node_type", "CMG"),
                    "alarm_id": row.get("alarm_id", f"ALM-{idx}"),
                    "alarm_code": alarm_code,
                    "alarm_name": row.get("alarm_name", alarm_code),
                    "alarm_type": row.get("type", "General"),
                    "severity": row.get("severity", "MAJOR"),
                    "timestamp": row["timestamp"],
                    "description": row.get("description", "")
                }

        scores = []
        for key, cand in candidates.items():
            score_breakdown = {}
            node = cand["node"]
            
            # 1. Earliest Onset (Max 30 pts)
            time_diff = (cand["timestamp"] - earliest_time).total_seconds()
            if time_diff == 0:
                onset_score = 30.0
            elif time_diff <= 30:
                onset_score = 22.0
            elif time_diff <= 120:
                onset_score = 12.0
            else:
                onset_score = 5.0
            score_breakdown["earliest_onset"] = onset_score

            # 2. Topology Position (Max 25 pts)
            if cand["node_type"] == "Transport":
                topo_score = 25.0
            elif cand["node_type"] == "CMG":
                # Control Plane Gateway is upstream of UPF user plane
                topo_score = 20.0
            elif node in self.topology_graph:
                out_deg = self.topology_graph.out_degree(node)
                topo_score = min(20.0, 10.0 + out_deg * 4.0)
            else:
                topo_score = 5.0
            score_breakdown["topology_position"] = topo_score

            # 3. Alarm Type Causality (Max 25 pts)
            a_type = cand["alarm_type"]
            a_code = cand["alarm_code"]
            if a_type == "Transport" or "LINK" in a_code:
                type_score = 25.0
            elif a_type == "Hardware" or "CPU" in a_code or "MEMORY" in a_code:
                type_score = 22.0
            elif a_type == "Protocol" or "BGP" in a_code or "PFCP" in a_code:
                type_score = 18.0
            else:
                type_score = 10.0
            score_breakdown["alarm_type_causality"] = type_score

            # 4. Symptoms Explained (Max 10 pts)
            explained_count = 0
            for other_alarm in alarms:
                if other_alarm.get("node") != node:
                    explained_count += 1
            symptoms_score = min(10.0, (explained_count / len(alarms)) * 10.0)
            score_breakdown["symptoms_explained"] = round(symptoms_score, 1)

            # 5. KPI Anomaly Support (Max 10 pts)
            kpi_score = 0.0
            if kpi_anomalies:
                for anom in kpi_anomalies:
                    if anom.get("node") == node:
                        kpi_score = 10.0
                        break
            if kpi_score == 0.0 and cand["severity"] in ["CRITICAL", "MAJOR"]:
                kpi_score = 7.0
            score_breakdown["kpi_anomaly_support"] = kpi_score

            total_score = round(sum(score_breakdown.values()), 1)
            
            explanation = (
                f"Candidate {node} [{cand['alarm_name']}] scored {total_score}/100 "
                f"(Onset: {onset_score}pt, Topo: {topo_score}pt, Type: {type_score}pt, "
                f"Symptoms: {score_breakdown['symptoms_explained']}pt, KPI: {kpi_score}pt)."
            )

            scores.append({
                "candidate_key": key,
                "node": node,
                "alarm_id": cand["alarm_id"],
                "alarm_name": cand["alarm_name"],
                "alarm_code": cand["alarm_code"],
                "total_score": total_score,
                "score_breakdown": score_breakdown,
                "explanation": explanation
            })

        scores.sort(key=lambda x: x["total_score"], reverse=True)
        top_root = scores[0]

        root_alarm_ids = {a.get("alarm_id", "") for a in alarms if a.get("node") == top_root["node"] and a.get("alarm_code") == top_root["alarm_code"]}
        
        symptoms = []
        for a in alarms:
            if a.get("alarm_id") not in root_alarm_ids:
                symptoms.append(f"{a.get('node', 'UNKNOWN')} - {a.get('alarm_name', 'Alarm')} ({a.get('alarm_code', '')})")

        severity = self.calculate_severity(alarms, incident.get("nodes_affected", []))

        incident["probable_root"] = f"{top_root['node']} ({top_root['alarm_name']})"
        incident["probable_root_node"] = top_root["node"]
        incident["probable_root_code"] = top_root["alarm_code"]
        incident["severity"] = severity
        incident["ranked_candidates"] = scores
        incident["symptoms"] = symptoms
        incident["score_breakdown"] = top_root["score_breakdown"]
        incident["ranking_explanation"] = top_root["explanation"]

        return incident
