from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import pandas as pd
from datetime import datetime

from app.config import settings
from app.ingest.loaders import DataLoader
from app.ingest.schemas import AlarmSchema
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker
from app.kpi.anomaly import KPIAnomalyChecker
from app.rag.retriever import RAGRetriever
from app.agent.tools import ToolRegistry
from app.agent.loop import TriageAgentLoop

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Network Health-Check and Alarm Triage Agent REST API",
    version="1.0.0",
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

# In-memory stores for notifications and tickets
notification_store: List[Dict[str, Any]] = []
ticket_store: Dict[str, Dict[str, Any]] = {}

# Pydantic Input/Output Request Models
class NotifyRequest(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "INC-20261008-001"})
    channel: str = Field(..., json_schema_extra={"example": "Teams"})
    recipient: str = Field(..., json_schema_extra={"example": "noc-engineering@telco.net"})
    message: str = Field(..., json_schema_extra={"example": "[CRITICAL] Triage complete for INC-20261008-001. Probable Root: LINK-A"})

class TicketRequest(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "INC-20261008-001"})
    title: str = Field(..., json_schema_extra={"example": "[CRITICAL] Physical Fiber Link Down on LINK-A"})
    severity: str = Field(..., json_schema_extra={"example": "CRITICAL"})
    description: str = Field(..., json_schema_extra={"example": "Automated draft ticket for LINK-A transport loss."})
    assignee: str = Field(default="NOC Tier-2")

# API Routes
@app.get("/health", tags=["Health"])
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "alarms_loaded": len(df_alarms),
        "kpis_loaded": len(df_kpi),
        "topology_nodes": list(G_topo.nodes)
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

@app.post("/notify", tags=["Notifications"])
def send_notification(payload: NotifyRequest):
    """Mock Teams / Email notification endpoint."""
    record = payload.model_dump()
    record["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    notification_store.append(record)
    return {
        "status": "delivered",
        "notification_id": f"NOTIF-{len(notification_store):04d}",
        "channel": payload.channel,
        "recipient": payload.recipient
    }

@app.get("/notifications", tags=["Notifications"])
def list_notifications():
    return {"total": len(notification_store), "notifications": notification_store}

@app.post("/ticket", tags=["Ticketing"])
def create_ticket(payload: TicketRequest):
    """Mock ITSM Ticket creation endpoint."""
    ticket_id = f"TICK-{payload.incident_id.replace('INC-', '')}"
    record = payload.model_dump()
    record["ticket_id"] = ticket_id
    record["created_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
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
