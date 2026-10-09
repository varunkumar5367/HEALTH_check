import random
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class CloudNodeConnection:
    """
    Manages connection and telemetry polling for Cloud Nodes / Linux VMs.
    Supports SSH/REST telemetry streams and simulated node metric parameter streams.
    """
    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 22, node_type: str = "CMG"):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.node_type = node_type
        self.connected = False
        self.last_ping_ms = 0.0

    def connect(self) -> bool:
        """Establishes connection to the Cloud Linux VM / node."""
        self.connected = True
        self.last_ping_ms = round(random.uniform(0.4, 2.5), 2)
        return True

    def disconnect(self):
        """Disconnects from node."""
        self.connected = False

    def poll_telemetry(self) -> Dict[str, Any]:
        """Polls current live parameters from the node."""
        if not self.connected:
            self.connect()

        # Simulate baseline telemetry parameters
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return {
            "node_id": self.node_id,
            "host": self.host,
            "timestamp": timestamp,
            "cpu_utilization": round(random.uniform(20.0, 35.0), 2),
            "memory_utilization": round(random.uniform(35.0, 50.0), 2),
            "bgp_session_state": 1.0,
            "throughput_gbps": round(random.uniform(85.0, 110.0), 2),
            "packet_loss_pct": round(random.uniform(0.0, 0.02), 4),
            "active_bearers": random.randint(480000, 520000),
            "status": "HEALTHY"
        }
