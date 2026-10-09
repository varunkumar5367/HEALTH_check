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
    KPI_ROLLING_WINDOW: int = 12
    KPI_Z_SCORE_THRESHOLD: float = 2.5
    
    # Agent Guardrails Config
    MAX_STEPS: int = 8
    CONFIDENCE_THRESHOLD: float = 0.70
    
    # Vector DB / Embeddings Config
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Cloud Node Monitoring & Email Alert Config
    MONITORING_INTERVAL_SECONDS: int = 5
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "varunakhil5367@gmail.com"
    SMTP_PASSWORD: str = "tnpwnlknepdakubk"
    ALERT_EMAIL_RECIPIENT: str = "varunakhil5367@gmail.com"
    SENDER_EMAIL: str = "varunakhil5367@gmail.com"

    class Config:
        case_sensitive = True

settings = Settings()
