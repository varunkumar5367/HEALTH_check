from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import pandas as pd
from datetime import datetime, timezone

from app.config import settings
from app.ingest.loaders import DataLoader
from app.ingest.schemas import AlarmSchema
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever
from app.agent.tools import ToolRegistry
from app.agent.loop import TriageAgentLoop
from app.notify.mailer import EmailDispatcher
from app.monitor.daemon import CloudNodeMonitorDaemon

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Network Health-Check, Cloud Monitoring, and Alarm Triage Agent REST API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global State & Singletons
loader = DataLoader()
df_alarms = loader.load_alarms()
G_topo = loader.load_topology_graph()
df_kpi = loader.load_kpis()

correlator = AlarmCorrelator(topology_graph=G_topo)
ranker = RootCauseRanker(topology_graph=G_topo)
anomaly_checker = KPIAnomalyChecker(kpi_df=df_kpi)
retriever = RAGRetriever()
tool_registry = ToolRegistry(loader=loader, anomaly_checker=anomaly_checker, retriever=retriever)
agent_loop = TriageAgentLoop(tool_registry=tool_registry, ranker=ranker)

mailer = EmailDispatcher()
monitor_daemon = CloudNodeMonitorDaemon(agent_loop=agent_loop, mailer=mailer)

# In-memory stores for notifications and tickets
notification_store: List[Dict[str, Any]] = []
ticket_store: Dict[str, Dict[str, Any]] = {}

# Pydantic Input/Output Request Models
class NotifyRequest(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "INC-20261008-001"})
    channel: str = Field(..., json_schema_extra={"example": "Teams"})
    recipient: str = Field(..., json_schema_extra={"example": "noc-engineering@telco.net"})
    message: str = Field(..., json_schema_extra={"example": "[CRITICAL] Triage complete for INC-20261008-001. Probable Root: LINK-A"})

class EmailRCAAlertRequest(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "INC-20261008-001"})
    recipient_email: str = Field(..., json_schema_extra={"example": "engineer@telco.com"})

class TicketRequest(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "INC-20261008-001"})
    title: str = Field(..., json_schema_extra={"example": "[CRITICAL] Physical Fiber Link Down on LINK-A"})
    severity: str = Field(..., json_schema_extra={"example": "CRITICAL"})
    description: str = Field(..., json_schema_extra={"example": "Automated draft ticket for LINK-A transport loss."})
    assignee: str = Field(default="NOC Tier-2")

class SimulateFaultRequest(BaseModel):
    node_id: str = Field(..., json_schema_extra={"example": "LINK-A"})
    alarm_code: str = Field(default="LINK_DOWN", json_schema_extra={"example": "LINK_DOWN"})
    alarm_name: str = Field(default="Physical Fiber Link Down", json_schema_extra={"example": "Physical Fiber Link Down"})
    recipient_email: Optional[str] = Field(default="noc-engineer@telco-ops.com")

# API Routes
@app.get("/health", tags=["Health"])
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "alarms_loaded": len(df_alarms),
        "kpis_loaded": len(df_kpi),
        "topology_nodes": list(G_topo.nodes),
        "monitoring_active": monitor_daemon.running
    }

@app.post("/alarms", tags=["Alarms"])
def ingest_alarms(alarms: List[AlarmSchema]):
    """Batch ingest of raw alarm records."""
    global df_alarms
    new_records = [a.model_dump() for a in alarms]
    new_df = pd.DataFrame(new_records)
    new_df["timestamp"] = pd.to_datetime(new_df["timestamp"])
    df_alarms = pd.concat([df_alarms, new_df], ignore_index=True)
    return {"status": "success", "ingested": len(new_records), "total_alarms": len(df_alarms)}

@app.get("/incidents", tags=["Triage"])
def list_incidents():
    """Lists all correlated incidents."""
    incidents = correlator.correlate(df_alarms)
    summaries = []
    for inc in incidents:
        ranked = ranker.rank_incident(inc)
        summaries.append({
            "id": ranked["id"],
            "title": ranked["title"],
            "start_time": ranked["start_time"],
            "end_time": ranked["end_time"],
            "nodes_affected": ranked["nodes_affected"],
            "total_alarms": ranked["total_alarms"],
            "probable_root": ranked["probable_root"],
            "severity": ranked["severity"]
        })
    return {"total_incidents": len(summaries), "incidents": summaries}

@app.get("/triage/{incident_id}", tags=["Triage"])
def get_triage(incident_id: str):
    """Retrieves end-to-end triage report, reasoning trace, citations, and draft ticket for an incident."""
    incidents = correlator.correlate(df_alarms)
    matched = [inc for inc in incidents if inc["id"] == incident_id]
    
    if not matched:
        try:
            idx = int(incident_id.split("-")[-1]) - 1
            if 0 <= idx < len(incidents):
                matched = [incidents[idx]]
        except Exception:
            pass
            
    if not matched:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
        
    triage_result = agent_loop.run_triage(matched[0])
    return triage_result

# Cloud Node Monitoring API Endpoints
@app.post("/monitor/start", tags=["Cloud Monitoring"])
def start_monitoring():
    """Starts continuous cloud node monitoring daemon."""
    monitor_daemon.start()
    return {"status": "started", "interval_seconds": monitor_daemon.interval_seconds}

@app.post("/monitor/stop", tags=["Cloud Monitoring"])
def stop_monitoring():
    """Stops continuous cloud node monitoring daemon."""
    monitor_daemon.stop()
    return {"status": "stopped"}

@app.get("/monitor/status", tags=["Cloud Monitoring"])
def get_monitoring_status():
    """Returns monitoring status and node connections."""
    return {
        "active": monitor_daemon.running,
        "nodes_monitored": [c.node_id for c in monitor_daemon.nodes],
        "total_events_logged": len(monitor_daemon.event_log),
        "recent_events": monitor_daemon.event_log[-5:]
    }

@app.post("/monitor/simulate-fault", tags=["Cloud Monitoring"])
def simulate_cloud_node_fault(payload: SimulateFaultRequest):
    """Simulates a parameter error on a cloud node, runs automated RCA, and emails solution report."""
    res = monitor_daemon.simulate_node_fault(
        node_id=payload.node_id,
        alarm_code=payload.alarm_code,
        alarm_name=payload.alarm_name,
        recipient_email=payload.recipient_email
    )
    return res

# Notification & Email Endpoints
@app.post("/notify", tags=["Notifications"])
def send_notification(payload: NotifyRequest):
    """Mock Teams / Email notification endpoint."""
    record = payload.model_dump()
    record["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    notification_store.append(record)
    return {
        "status": "delivered",
        "notification_id": f"NOTIF-{len(notification_store):04d}",
        "channel": payload.channel,
        "recipient": payload.recipient
    }

@app.post("/notify/email", tags=["Notifications"])
def dispatch_rca_email(payload: EmailRCAAlertRequest):
    """Triggers automated RCA & Cited Solution HTML Email dispatch to engineer."""
    incidents = correlator.correlate(df_alarms)
    matched = [inc for inc in incidents if inc["id"] == payload.incident_id]
    if not matched:
        try:
            idx = int(payload.incident_id.split("-")[-1]) - 1
            if 0 <= idx < len(incidents):
                matched = [incidents[idx]]
        except Exception:
            pass
    if not matched:
        raise HTTPException(status_code=404, detail=f"Incident {payload.incident_id} not found.")

    triage_result = agent_loop.run_triage(matched[0])
    email_res = mailer.send_rca_email(triage_result, recipient=payload.recipient_email)
    return {"status": "email_sent", "email_details": email_res}

@app.get("/notify/outbox", tags=["Notifications"])
def get_email_outbox():
    """Returns outbox history of all dispatched RCA emails."""
    return {"total_emails": len(mailer.outbox_history), "outbox": mailer.outbox_history}

@app.post("/ticket", tags=["Ticketing"])
def create_ticket(payload: TicketRequest):
    """Mock ITSM Ticket creation endpoint."""
    ticket_id = f"TICK-{payload.incident_id.replace('INC-', '')}"
    record = payload.model_dump()
    record["ticket_id"] = ticket_id
    record["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ticket_store[ticket_id] = record
    return {
        "status": "created",
        "ticket_id": ticket_id,
        "ticket": record
    }

# Diagnostic REST Tool Endpoints
@app.get("/tools/ping", tags=["Diagnostic Tools"])
def tool_ping(node: str):
    return tool_registry.ping(node)

@app.get("/tools/kpi", tags=["Diagnostic Tools"])
def tool_kpi(node: str, kpi: str, window_minutes: int = 15):
    return tool_registry.get_kpi(node, kpi, window_minutes)

@app.get("/tools/status", tags=["Diagnostic Tools"])
def tool_status(node: str):
    return tool_registry.show_status(node)

@app.get("/tools/topology", tags=["Diagnostic Tools"])
def tool_topology(node: str):
    return tool_registry.topology_neighbors(node)
