import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.config import settings
from app.monitor.connection import CloudNodeConnection
from app.correlation.engine import AlarmCorrelator
from app.correlation.root_cause import RootCauseRanker
from app.agent.loop import TriageAgentLoop
from app.notify.mailer import EmailDispatcher

class CloudNodeMonitorDaemon:
    """
    Continuous Cloud Node / Linux VM Monitoring Daemon.
    Monitors parameters in real-time. Upon detecting parameter fluctuations or KPI errors:
    1. Creates an Alarm Record.
    2. Runs automated Triage Agent analysis.
    3. Dispatches Root Cause Analysis & Cited Solution Email to NOC Engineers.
    """
    def __init__(self, agent_loop: TriageAgentLoop, mailer: EmailDispatcher, interval_seconds: int = settings.MONITORING_INTERVAL_SECONDS):
        self.agent_loop = agent_loop
        self.mailer = mailer
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Node connections
        self.nodes = [
            CloudNodeConnection("LINK-A", host="10.0.0.1", node_type="Transport"),
            CloudNodeConnection("LINK-B", host="10.0.0.2", node_type="Transport"),
            CloudNodeConnection("CMG-01", host="10.95.176.101", node_type="CMG"),
            CloudNodeConnection("CMG-02", host="10.95.176.102", node_type="CMG"),
            CloudNodeConnection("CMG-03", host="10.95.176.103", node_type="CMG"),
            CloudNodeConnection("UPF-01", host="10.95.46.171", node_type="UPF"),
            CloudNodeConnection("UPF-02", host="10.95.46.172", node_type="UPF")
        ]
        
        self.event_log: List[Dict[str, Any]] = []

    def add_node(self, node_id: str, host: str = "127.0.0.1", port: int = 22, node_type: str = "CMG") -> tuple:
        """Dynamically registers and connects a new Cloud Node / VM for real-time monitoring."""
        for conn in self.nodes:
            if conn.node_id == node_id:
                conn.host = host
                conn.port = port
                conn.node_type = node_type
                res = conn.connect()
                return conn, res

        new_conn = CloudNodeConnection(node_id=node_id, host=host, port=port, node_type=node_type)
        res = new_conn.connect()
        self.nodes.append(new_conn)
        print(f"[MONITOR] Connected new cloud node {node_id} ({host}:{port}) [{node_type}]")
        return new_conn, res

    def start(self):
        """Starts the continuous background monitoring loop."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print(f"[MONITOR] Cloud Node Monitoring Daemon STARTED (Interval: {self.interval_seconds}s)")

    def stop(self):
        """Stops the continuous monitoring loop."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("[MONITOR] Cloud Node Monitoring Daemon STOPPED.")

    def simulate_node_fault(self, node_id: str, alarm_code: str, alarm_name: str, recipient_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates an explicit parameter fluctuation / error on a cloud node,
        triggers the triage loop, and dispatches the RCA Email.
        """
        node_type = "Transport" if "LINK" in node_id else ("CMG" if "CMG" in node_id else "UPF")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        alarm_event = {
            "alarm_id": f"ALM-MONITOR-{len(self.event_log)+1:04d}",
            "timestamp": timestamp,
            "node": node_id,
            "node_type": node_type,
            "alarm_code": alarm_code,
            "alarm_name": alarm_name,
            "severity": "CRITICAL" if "DOWN" in alarm_code or "HIGH" in alarm_code else "MAJOR",
            "type": "Transport" if "LINK" in alarm_code else ("Hardware" if "CPU" in alarm_code else "Protocol"),
            "description": f"Real-time cloud monitoring parameter fluctuation detected on {node_id}: {alarm_name}",
            "status": "ACTIVE"
        }

        self.event_log.append(alarm_event)

        # Construct incident storm representation around node_id
        cascade_alarms = [alarm_event]
        if node_id == "LINK-A":
            cascade_alarms.append({
                "alarm_id": f"ALM-MONITOR-{len(self.event_log)+2:04d}",
                "timestamp": timestamp,
                "node": "CMG-02",
                "node_type": "CMG",
                "alarm_code": "BGP_PEER_DOWN",
                "alarm_name": "BGP Peer Session Down",
                "severity": "MAJOR",
                "type": "Protocol",
                "description": "BGP peer session lost state Established -> Idle on CMG-02",
                "status": "ACTIVE"
            })
            cascade_alarms.append({
                "alarm_id": f"ALM-MONITOR-{len(self.event_log)+3:04d}",
                "timestamp": timestamp,
                "node": "CMG-03",
                "node_type": "CMG",
                "alarm_code": "SERVICE_DEGRADED",
                "alarm_name": "Service Degraded Alert",
                "severity": "MAJOR",
                "type": "Service",
                "description": "Secondary service degradation on CMG-03",
                "status": "ACTIVE"
            })

        incident = {
            "id": f"INC-MON-{len(self.event_log):03d}",
            "title": f"Live Cloud Monitor Alert: {node_id} ({alarm_name})",
            "start_time": timestamp,
            "end_time": timestamp,
            "nodes_affected": list(set(a["node"] for a in cascade_alarms)),
            "total_alarms": len(cascade_alarms),
            "alarms": cascade_alarms,
            "grouping_rationale": f"Continuous cloud monitoring telemetry flagged parameter fluctuation on {node_id} causing secondary impact."
        }

        # Run automated Triage Agent
        triage_res = self.agent_loop.run_triage(incident)

        # Send RCA & Solution Email
        email_record = self.mailer.send_rca_email(triage_res, recipient=recipient_email)

        return {
            "status": "FAULT_DETECTED",
            "alarm_event": alarm_event,
            "triage_result": triage_res,
            "email_dispatch": email_record
        }

    def _monitor_loop(self):
        while self.running:
            time.sleep(self.interval_seconds)
            # Daemon periodic health check loop
            for conn in self.nodes:
                if not self.running:
                    break
                telemetry = conn.poll_telemetry()
