from typing import Dict, Any, List
import pandas as pd

from app.config import settings
from app.agent.tools import ToolRegistry
from app.correlation.root_cause import RootCauseRanker

class TriageAgentLoop:
    """
    Agent Triage Execution Loop (Observe -> Hypothesise -> Act -> Evaluate -> Conclude).
    Enforces strict guardrails: MAX_STEPS (8), read-only tools, confidence thresholding,
    and structured reasoning traces.
    """
    def __init__(self, tool_registry: ToolRegistry, ranker: RootCauseRanker, max_steps: int = settings.MAX_STEPS, confidence_threshold: float = settings.CONFIDENCE_THRESHOLD):
        self.tools = tool_registry
        self.ranker = ranker
        self.max_steps = max_steps
        self.confidence_threshold = confidence_threshold

    def run_triage(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        reasoning_trace = []
        incident_id = incident.get("id", "INC-000")
        alarms = incident.get("alarms", [])
        nodes = incident.get("nodes_affected", [])

        # STEP 1: OBSERVE
        step_1_obs = {
            "step": 1,
            "action": "OBSERVE",
            "tool": "incident_ingest",
            "input": {"incident_id": incident_id, "total_alarms": len(alarms), "nodes": nodes},
            "output": f"Observed {len(alarms)} grouped alarms across nodes {nodes}.",
            "conclusion": f"Incident spans {len(nodes)} nodes. Initiating diagnostic investigation."
        }
        reasoning_trace.append(step_1_obs)

        # STEP 2: HYPOTHESISE & RANK CANDIDATES
        ranked_inc = self.ranker.rank_incident(incident)
        top_root_node = ranked_inc.get("probable_root_node", nodes[0] if nodes else "UNKNOWN")
        top_root_code = ranked_inc.get("probable_root_code", "UNKNOWN")
        confidence_score = min(0.95, ranked_inc.get("score_breakdown", {}).get("total_score", 75.0) / 100.0)
        
        step_2_hypo = {
            "step": 2,
            "action": "HYPOTHESISE",
            "tool": "root_cause_ranker",
            "input": {"candidates": len(ranked_inc.get("ranked_candidates", []))},
            "output": f"Initial ranking hypothesis: Root node = {top_root_node}, code = {top_root_code}.",
            "conclusion": f"Hypothesised probable root cause: {top_root_node} ({top_root_code}). Score: {confidence_score*100:.1f}/100."
        }
        reasoning_trace.append(step_2_hypo)

        # STEP 3: ACT (Ping Root & Neighbor Nodes)
        ping_res = self.tools.ping(top_root_node)
        step_3_act = {
            "step": 3,
            "action": "ACT",
            "tool": "ping",
            "input": {"node": top_root_node},
            "output": ping_res,
            "conclusion": f"Node {top_root_node} status: {ping_res.get('status')}, loss: {ping_res.get('packet_loss_pct')}%."
        }
        reasoning_trace.append(step_3_act)

        # STEP 4: ACT (Check Topology Neighbors)
        topo_res = self.tools.topology_neighbors(top_root_node)
        step_4_act = {
            "step": 4,
            "action": "ACT",
            "tool": "topology_neighbors",
            "input": {"node": top_root_node},
            "output": topo_res,
            "conclusion": f"Topological neighbors of {top_root_node}: {topo_res.get('neighbors')}."
        }
        reasoning_trace.append(step_4_act)

        # STEP 5: ACT (Check KPI Anomalies)
        kpi_name = "bgp_session_state" if "BGP" in top_root_code else ("cpu_utilization" if "CPU" in top_root_code else "throughput_gbps")
        kpi_res = self.tools.get_kpi(top_root_node, kpi_name, 15)
        step_5_act = {
            "step": 5,
            "action": "ACT",
            "tool": "get_kpi",
            "input": {"node": top_root_node, "kpi": kpi_name},
            "output": kpi_res,
            "conclusion": f"KPI {kpi_name} on {top_root_node} has_anomaly={kpi_res.get('has_anomaly')}."
        }
        reasoning_trace.append(step_5_act)

        # STEP 6: ACT (Search Runbooks for Cited Next Checks)
        node_type = alarms[0].get("node_type", "") if alarms else ""
        runbook_checks = self.tools.search_runbook(top_root_code, node_type=node_type)
        step_6_act = {
            "step": 6,
            "action": "ACT",
            "tool": "search_runbook",
            "input": {"query": top_root_code, "node_type": node_type},
            "output": runbook_checks,
            "conclusion": f"Retrieved {len(runbook_checks)} cited runbook checks."
        }
        reasoning_trace.append(step_6_act)

        # STEP 7: EVALUATE & GUARDRAIL CHECK
        needs_escalation = False
        escalation_reason = ""
        if len(reasoning_trace) > self.max_steps:
            needs_escalation = True
            escalation_reason = f"Max steps ({self.max_steps}) exceeded."
        elif confidence_score < self.confidence_threshold:
            needs_escalation = True
            escalation_reason = f"Confidence score ({confidence_score:.2f}) below threshold ({self.confidence_threshold}). Low confidence, engineer review needed."

        step_7_eval = {
            "step": 7,
            "action": "EVALUATE",
            "tool": "guardrail_evaluator",
            "input": {"steps_taken": len(reasoning_trace), "confidence": confidence_score},
            "output": {"escalate": needs_escalation, "reason": escalation_reason},
            "conclusion": "Evaluation clean. Confidence meets operational threshold." if not needs_escalation else escalation_reason
        }
        reasoning_trace.append(step_7_eval)

        # STEP 8: CONCLUDE
        past_incidents = self.tools.search_past_incidents(f"{top_root_node} {top_root_code}")
        
        draft_ticket = self._generate_draft_ticket(
            incident_id=incident_id,
            probable_root=ranked_inc.get("probable_root"),
            severity=ranked_inc.get("severity"),
            nodes=nodes,
            checks=runbook_checks,
            symptoms=ranked_inc.get("symptoms", [])
        )

        step_8_conclude = {
            "step": 8,
            "action": "CONCLUDE",
            "tool": "triage_summary",
            "input": {"incident_id": incident_id},
            "output": "Triage analysis complete.",
            "conclusion": f"Final Triage Result: Root = {ranked_inc.get('probable_root')}, Severity = {ranked_inc.get('severity')}."
        }
        reasoning_trace.append(step_8_conclude)

        return {
            "incident_id": incident_id,
            "probable_root": ranked_inc.get("probable_root"),
            "probable_root_node": top_root_node,
            "probable_root_code": top_root_code,
            "severity": ranked_inc.get("severity"),
            "confidence_score": round(confidence_score, 2),
            "status": "HANDOVER_ENGINEER_REVIEW" if needs_escalation else "TRIAGED",
            "grouping_rationale": ranked_inc.get("grouping_rationale"),
            "symptoms": ranked_inc.get("symptoms", []),
            "cited_next_checks": runbook_checks,
            "similar_past_incidents": past_incidents,
            "draft_ticket": draft_ticket,
            "reasoning_trace": reasoning_trace
        }

    def _generate_draft_ticket(self, incident_id: str, probable_root: str, severity: str, nodes: List[str], checks: List[Dict[str, str]], symptoms: List[str]) -> Dict[str, Any]:
        check_str = "\n".join([f"- [{c.get('citation')}] {c.get('content', '')[:100]}..." for c in checks[:3]])
        
        description = (
            f"INCIDENT SUMMARY: {incident_id}\n"
            f"Probable Root Cause: {probable_root}\n"
            f"Assigned Severity: {severity}\n"
            f"Nodes Affected: {', '.join(nodes)}\n\n"
            f"CITED RUNBOOK CHECKS:\n{check_str}\n\n"
            f"GROUPED SYMPTOMS ({len(symptoms)}):\n" + "\n".join([f"- {s}" for s in symptoms[:5]])
        )
        
        return {
            "ticket_id": f"TICK-{incident_id.replace('INC-', '')}",
            "title": f"[{severity}] Triage Alert: Root Cause {probable_root}",
            "severity": severity,
            "assignee": "NOC/SNOC Tier-2 Engineering",
            "description": description,
            "created_at": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
