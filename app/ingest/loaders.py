import pandas as pd
import json
import networkx as nx
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

from app.config import settings
from app.ingest.schemas import AlarmSchema, KPIRecord, TopologyGraphData

class DataLoader:
    """
    Unified Data Loader for Alarms, KPIs, Topology Graph, Runbooks, and Past Incidents.
    """
    def __init__(self, data_dir: Path = settings.DATA_DIR):
        self.data_dir = data_dir

    def load_alarms(self) -> pd.DataFrame:
        alarms_path = self.data_dir / "alarms.csv"
        if not alarms_path.exists():
            raise FileNotFoundError(f"Alarms file not found at {alarms_path}")
        df = pd.read_csv(alarms_path)
        # Parse timestamps to pandas datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def load_kpis(self) -> pd.DataFrame:
        kpi_path = self.data_dir / "kpi_data.csv"
        if not kpi_path.exists():
            raise FileNotFoundError(f"KPI file not found at {kpi_path}")
        df = pd.read_csv(kpi_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def load_topology_graph(self) -> nx.DiGraph:
        topo_path = self.data_dir / "topology.json"
        if not topo_path.exists():
            raise FileNotFoundError(f"Topology file not found at {topo_path}")
            
        with open(topo_path, "r") as f:
            data = json.load(f)
            
        G = nx.DiGraph()
        for node in data.get("nodes", []):
            G.add_node(node["id"], **node)
            
        for edge in data.get("edges", []):
            G.add_edge(edge["source"], edge["target"], link_type=edge.get("link_type", "Transport"))
            # Make graph undirected for reachability / shortest path distance
            G.add_edge(edge["target"], edge["source"], link_type=edge.get("link_type", "Transport"))
            
        return G

    def load_runbooks(self) -> List[Dict[str, str]]:
        runbooks_dir = self.data_dir / "runbooks"
        docs = []
        if not runbooks_dir.exists():
            return docs
            
        for file_path in runbooks_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            doc_name = file_path.name
            # Extract sections
            sections = content.split("\n## ")
            title = sections[0].replace("# ", "").strip()
            
            for sec in sections[1:]:
                lines = sec.split("\n")
                heading = lines[0].strip()
                body = "\n".join(lines[1:]).strip()
                docs.append({
                    "id": f"{doc_name}#{heading}",
                    "runbook_name": doc_name,
                    "section_heading": heading,
                    "title": title,
                    "content": body,
                    "full_text": f"{title} - {heading}:\n{body}"
                })
        return docs

    def load_past_incidents(self) -> List[Dict[str, str]]:
        incidents_dir = self.data_dir / "past_incidents"
        incidents = []
        if not incidents_dir.exists():
            return incidents
            
        for file_path in incidents_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            incidents.append({
                "id": file_path.stem,
                "filename": file_path.name,
                "content": content
            })
        return incidents
