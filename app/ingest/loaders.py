import pandas as pd
import json
import networkx as nx
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import glob
import os

from app.config import settings
from app.ingest.schemas import AlarmSchema, KPIRecord, TopologyGraphData

class DataLoader:
    """
    Unified Data Loader for Alarms, KPIs, Topology Graph, Runbooks, Past Incidents,
    and raw PS06 Hackathon input files.
    """
    def __init__(self, data_dir: Path = settings.DATA_DIR, raw_dir: Path = settings.RAW_DATA_DIR):
        self.data_dir = data_dir
        self.raw_dir = raw_dir

    def load_alarms(self) -> pd.DataFrame:
        alarms_path = self.data_dir / "alarms.csv"
        if not alarms_path.exists():
            raise FileNotFoundError(f"Alarms file not found at {alarms_path}")
        df = pd.read_csv(alarms_path)
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
            G.add_edge(edge["target"], edge["source"], link_type=edge.get("link_type", "Transport"))
            
        return G

    def load_runbooks(self) -> List[Dict[str, str]]:
        runbooks_dir = self.data_dir / "runbooks"
        docs = []
        if runbooks_dir.exists():
            for file_path in runbooks_dir.glob("*.md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                doc_name = file_path.name
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

        # ALSO load raw PS06 hackathon documents from Supported Commands & Logs
        raw_ps06_docs = self.load_ps06_raw_documents()
        docs.extend(raw_ps06_docs)

        return docs

    def load_ps06_raw_documents(self) -> List[Dict[str, str]]:
        """
        Parses and chunks raw PS06 text files from Supported Commands & Alarms/Logs Outputs.
        """
        ps06_docs = []
        search_dirs = [
            Path(r"C:\Users\varun\Downloads\Hackathon_Central_Data\PS06"),
            self.raw_dir
        ]

        for s_dir in search_dirs:
            if not s_dir.exists():
                continue
                
            # Supported Commands
            supp_dir = s_dir / "Supported Commands"
            if supp_dir.exists():
                for txt_file in supp_dir.glob("*.txt"):
                    try:
                        with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                            
                        # Chunk by command blocks
                        blocks = text.split("+++++++++++++++++++++++++++++++++++++++++++++++")
                        for idx, block in enumerate(blocks):
                            b_clean = block.strip()
                            if len(b_clean) > 20:
                                heading = f"Command Check Block {idx+1}"
                                ps06_docs.append({
                                    "id": f"PS06_{txt_file.name}#{heading}",
                                    "runbook_name": f"PS06_{txt_file.name}",
                                    "section_heading": heading,
                                    "title": f"Nokia Supported Commands ({txt_file.stem})",
                                    "content": b_clean,
                                    "full_text": f"Nokia Supported Commands ({txt_file.stem}) - {heading}:\n{b_clean}"
                                })
                    except Exception as e:
                        print(f"Error loading {txt_file}: {e}")

        return ps06_docs

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
