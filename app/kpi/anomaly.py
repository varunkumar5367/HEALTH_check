import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.config import settings
from app.ingest.loaders import DataLoader

class KPIAnomalyChecker:
    """
    Direction-aware Z-score and rolling baseline anomaly detector for network node KPIs.
    """
    def __init__(self, kpi_df: pd.DataFrame, window_size: int = settings.KPI_ROLLING_WINDOW, z_threshold: float = settings.KPI_Z_SCORE_THRESHOLD):
        self.df = kpi_df.copy()
        self.window_size = window_size
        self.z_threshold = z_threshold
        if "timestamp" in self.df.columns and not pd.api.types.is_datetime64_any_dtype(self.df["timestamp"]):
            self.df["timestamp"] = pd.to_datetime(self.df["timestamp"])
        self.df.sort_values(by=["node", "kpi_name", "timestamp"], inplace=True)

    def get_kpi(self, node: str, kpi_name: str, window_minutes: int = 15) -> pd.DataFrame:
        """
        Retrieves recent KPI timeseries records for a specific node and metric within the window.
        """
        sub_df = self.df[(self.df["node"] == node) & (self.df["kpi_name"] == kpi_name)]
        if sub_df.empty:
            return pd.DataFrame()
            
        latest_time = sub_df["timestamp"].max()
        start_time = latest_time - timedelta(minutes=window_minutes)
        return sub_df[sub_df["timestamp"] >= start_time].copy()

    def check_node_anomalies(self, node: str, timestamp_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Evaluates directional z-score anomalies for a given node at or near a timestamp.
        """
        anomalies = []
        node_df = self.df[self.df["node"] == node]
        if node_df.empty:
            return anomalies

        target_time = pd.to_datetime(timestamp_str) if timestamp_str else node_df["timestamp"].max()
        
        # Unique KPI names for this node
        kpi_names = node_df["kpi_name"].unique()
        
        for kpi in kpi_names:
            k_df = node_df[node_df["kpi_name"] == kpi].copy()
            if len(k_df) < 3:
                continue
                
            # Filter up to target_time
            hist_df = k_df[k_df["timestamp"] <= target_time].tail(self.window_size + 1)
            if hist_df.empty:
                continue
                
            current_row = hist_df.iloc[-1]
            curr_val = current_row["value"]
            
            baseline = hist_df.iloc[:-1]["value"] if len(hist_df) > 1 else hist_df["value"]
            mean_val = baseline.mean()
            std_val = baseline.std() if len(baseline) > 1 else 0.0
            
            z_score = 0.0 if std_val == 0.0 else (curr_val - mean_val) / std_val
            
            # Direction-aware logic
            is_anomalous = False
            direction = "NORMAL"
            
            if kpi in ["cpu_utilization", "memory_utilization", "packet_loss_pct"]:
                # High is bad
                if curr_val > 80.0 or z_score >= self.z_threshold:
                    is_anomalous = True
                    direction = "HIGH_ANOMALY"
            elif kpi == "bgp_session_state":
                # Low is bad (1.0 = UP, 0.0 = DOWN)
                if curr_val < 0.5 or z_score <= -self.z_threshold:
                    is_anomalous = True
                    direction = "DOWN_ANOMALY"
            elif kpi in ["throughput_gbps", "active_bearers"]:
                # Deviation either way, drop is severe
                if abs(z_score) >= self.z_threshold or (mean_val > 0 and curr_val < 0.3 * mean_val):
                    is_anomalous = True
                    direction = "DROP_ANOMALY" if curr_val < mean_val else "SPIKE_ANOMALY"
            else:
                if abs(z_score) >= self.z_threshold:
                    is_anomalous = True
                    direction = "DEVIATION"

            if is_anomalous:
                anomalies.append({
                    "node": node,
                    "kpi_name": kpi,
                    "timestamp": current_row["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "value": round(float(curr_val), 2),
                    "baseline_mean": round(float(mean_val), 2),
                    "z_score": round(float(z_score), 2),
                    "direction": direction,
                    "summary": f"KPI {kpi} on {node} anomaly ({direction}): val={curr_val}, mean={mean_val:.1f}, Z={z_score:.2f}"
                })
                
        return anomalies
