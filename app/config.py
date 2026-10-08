from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Network Health-Check and Alarm Triage Agent"
    API_V1_STR: str = "/api/v1"
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = BASE_DIR / "raw_data"
    
    # Files
    ALARMS_FILE: Path = DATA_DIR / "alarms.csv"
    TOPOLOGY_FILE: Path = DATA_DIR / "topology.json"
    KPI_FILE: Path = DATA_DIR / "kpi_data.csv"
    RUNBOOKS_DIR: Path = DATA_DIR / "runbooks"
    PAST_INCIDENTS_DIR: Path = DATA_DIR / "past_incidents"
    
    # Incident Correlation Config
    TIME_WINDOW_MINUTES: int = 5
    TOPOLOGY_MAX_HOPS: int = 2
    
    # KPI Anomaly Config
    KPI_ROLLING_WINDOW: int = 12  # e.g. 12 data points (1 hour at 5-min intervals)
    KPI_Z_SCORE_THRESHOLD: float = 2.5
    
    # Agent Guardrails Config
    MAX_STEPS: int = 8
    CONFIDENCE_THRESHOLD: float = 0.70
    
    # Vector DB / Embeddings Config
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    class Config:
        case_sensitive = True

settings = Settings()
