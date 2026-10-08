from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class AlarmSchema(BaseModel):
    alarm_id: str = Field(..., description="Unique Alarm ID")
    timestamp: datetime = Field(..., description="Timestamp of alarm occurrence")
    node: str = Field(..., description="Node name e.g. LINK-A, CMG-02")
    node_type: str = Field(..., description="Node type e.g. Transport, CMG, UPF")
    alarm_code: str = Field(..., description="Short alarm code e.g. LINK_DOWN")
    alarm_name: str = Field(..., description="Human readable alarm name")
    severity: str = Field(..., description="Severity: CRITICAL, MAJOR, MINOR, WARNING")
    type: str = Field(..., description="Alarm category e.g. Transport, Protocol, Service, Hardware")
    description: str = Field(..., description="Detailed explanation of the alarm")
    status: str = Field(default="ACTIVE", description="Status: ACTIVE or CLEARED")

class KPIRecord(BaseModel):
    timestamp: datetime
    node: str
    kpi_name: str
    value: float
    unit: Optional[str] = None
    suspect: Optional[bool] = False

class TopologyNode(BaseModel):
    id: str
    name: str
    node_type: str
    site: Optional[str] = "Agra"

class TopologyEdge(BaseModel):
    source: str
    target: str
    link_type: str = "Transport"

class TopologyGraphData(BaseModel):
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]

class IncidentSummary(BaseModel):
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    nodes_affected: List[str]
    total_alarms: int
    probable_root: str
    probable_root_node: str
    severity: str
    grouping_rationale: str
    score_breakdown: Dict[str, float]
    symptoms: List[str]
