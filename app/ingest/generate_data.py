import json
import pandas as pd
from datetime import datetime, timedelta
import random
from pathlib import Path
import os

from app.config import settings

def generate_topology():
    topology = {
        "nodes": [
            {"id": "LINK-A", "name": "Transport Link A", "node_type": "Transport", "site": "Agra Core"},
            {"id": "LINK-B", "name": "Transport Link B", "node_type": "Transport", "site": "Agra Edge"},
            {"id": "CMG-01", "name": "Control Plane Gateway 01", "node_type": "CMG", "site": "Agra Core"},
            {"id": "CMG-02", "name": "Control Plane Gateway 02", "node_type": "CMG", "site": "Agra Core"},
            {"id": "CMG-03", "name": "Control Plane Gateway 03", "node_type": "CMG", "site": "Agra Core"},
            {"id": "UPF-01", "name": "User Plane Function 01", "node_type": "UPF", "site": "Agra South"},
            {"id": "UPF-02", "name": "User Plane Function 02", "node_type": "UPF", "site": "Agra South"},
        ],
        "edges": [
            {"source": "LINK-A", "target": "CMG-02", "link_type": "Transport"},
            {"source": "LINK-A", "target": "CMG-03", "link_type": "Transport"},
            {"source": "CMG-02", "target": "CMG-03", "link_type": "BGP_Peer"},
            {"source": "CMG-01", "target": "UPF-01", "link_type": "PFCP_S5S8"},
            {"source": "CMG-02", "target": "UPF-01", "link_type": "PFCP_S5S8"},
            {"source": "CMG-03", "target": "UPF-02", "link_type": "PFCP_S5S8"},
            {"source": "LINK-B", "target": "UPF-01", "link_type": "Transport"},
            {"source": "LINK-B", "target": "UPF-02", "link_type": "Transport"},
        ]
    }
    
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(settings.TOPOLOGY_FILE, "w") as f:
        json.dump(topology, f, indent=2)
    print(f"Topology generated at {settings.TOPOLOGY_FILE}")

def generate_alarms():
    alarms = []
    base_time = datetime(2026, 10, 8, 10, 0, 0)
    
    # -------------------------------------------------------------
    # STORM 1: Sample Scenario (40 alarms in 5 mins: 10:00:00 - 10:05:00)
    # Root: LINK-A down -> BGP peer down CMG-02 -> Service degradation CMG-02/CMG-03
    # -------------------------------------------------------------
    # Root Cause Alarm at 10:00:00
    alarms.append({
        "alarm_id": "ALM-STORM1-001",
        "timestamp": (base_time).isoformat() + "Z",
        "node": "LINK-A",
        "node_type": "Transport",
        "alarm_code": "LINK_DOWN",
        "alarm_name": "Physical Fiber Link Down",
        "severity": "CRITICAL",
        "type": "Transport",
        "description": "Primary fiber optical path loss of signal detected on interface Port 1/1/1",
        "status": "ACTIVE"
    })
    
    # Cascade 1: BGP peer down on CMG-02 at 10:00:30
    alarms.append({
        "alarm_id": "ALM-STORM1-002",
        "timestamp": (base_time + timedelta(seconds=30)).isoformat() + "Z",
        "node": "CMG-02",
        "node_type": "CMG",
        "alarm_code": "BGP_PEER_DOWN",
        "alarm_name": "BGP Peer Session Down",
        "severity": "MAJOR",
        "type": "Protocol",
        "description": "BGP peer neighbor 192.168.1.1 session lost state Established -> Idle",
        "status": "ACTIVE"
    })
    
    # Cascade 2: Service degradation on CMG-02 and CMG-03 (38 symptom alarms)
    for i in range(3, 41):
        t_offset = timedelta(seconds=random.randint(40, 290))
        node = random.choice(["CMG-02", "CMG-03"])
        alarm_code = random.choice(["SERVICE_DEGRADED", "GTP_PATH_FAIL", "ATTACH_FAIL_HIGH", "BEARER_DROP"])
        severity = random.choice(["MAJOR", "MINOR", "WARNING"])
        alarms.append({
            "alarm_id": f"ALM-STORM1-{i:03d}",
            "timestamp": (base_time + t_offset).isoformat() + "Z",
            "node": node,
            "node_type": "CMG",
            "alarm_code": alarm_code,
            "alarm_name": f"{alarm_code.replace('_', ' ').title()} Alert",
            "severity": severity,
            "type": "Service",
            "description": f"Service performance degraded on {node} due to upstream transport failure",
            "status": "ACTIVE"
        })

    # -------------------------------------------------------------
    # STORM 2: CMG-01 CPU/Memory Exhaustion (80 alarms, 12:00:00 - 12:05:00)
    # Root: CMG-01 CPU_HIGH -> GTP Path Mgmt Failure & UPF-01 Session Drops
    # -------------------------------------------------------------
    base_time2 = datetime(2026, 10, 8, 12, 0, 0)
    alarms.append({
        "alarm_id": "ALM-STORM2-001",
        "timestamp": base_time2.isoformat() + "Z",
        "node": "CMG-01",
        "node_type": "CMG",
        "alarm_code": "CPU_HIGH",
        "alarm_name": "CPU Utilization Exceeds Threshold",
        "severity": "CRITICAL",
        "type": "Hardware",
        "description": "CPM slot 1 CPU utilization exceeded 98% threshold for >30s",
        "status": "ACTIVE"
    })
    
    for i in range(2, 81):
        t_offset = timedelta(seconds=random.randint(5, 295))
        node = "CMG-01" if i % 2 == 0 else "UPF-01"
        alarm_code = random.choice(["GTP_PATH_FAIL", "MEMORY_HIGH", "SESSION_DROP", "PFCP_TIMEOUT"])
        severity = random.choice(["CRITICAL", "MAJOR", "MINOR"])
        alarms.append({
            "alarm_id": f"ALM-STORM2-{i:03d}",
            "timestamp": (base_time2 + t_offset).isoformat() + "Z",
            "node": node,
            "node_type": "CMG" if node == "CMG-01" else "UPF",
            "alarm_code": alarm_code,
            "alarm_name": f"{alarm_code.replace('_', ' ').title()} Alert",
            "severity": severity,
            "type": "Service" if "DROP" in alarm_code or "GTP" in alarm_code else "Hardware",
            "description": f"Resource exhaustion secondary impact on {node}",
            "status": "ACTIVE"
        })

    # -------------------------------------------------------------
    # STORM 3: PFCP Heartbeat Failure (70 alarms, 14:00:00 - 14:05:00)
    # Root: CMG-03 PFCP_HEARTBEAT_FAIL -> UPF-02 Bearer Creation Failure
    # -------------------------------------------------------------
    base_time3 = datetime(2026, 10, 8, 14, 0, 0)
    alarms.append({
        "alarm_id": "ALM-STORM3-001",
        "timestamp": base_time3.isoformat() + "Z",
        "node": "CMG-03",
        "node_type": "CMG",
        "alarm_code": "PFCP_HEARTBEAT_FAIL",
        "alarm_name": "PFCP Association Heartbeat Timeout",
        "severity": "CRITICAL",
        "type": "Protocol",
        "description": "N4/Sxa/Sxb PFCP heartbeat response timeout with UPF-02 (10.95.46.177)",
        "status": "ACTIVE"
    })
    
    for i in range(2, 71):
        t_offset = timedelta(seconds=random.randint(10, 290))
        node = "UPF-02" if i % 2 == 0 else "CMG-03"
        alarm_code = random.choice(["BEARER_CREATE_FAIL", "S5_GTP_FAIL", "USER_PLANE_ISOLATED"])
        severity = random.choice(["MAJOR", "MINOR"])
        alarms.append({
            "alarm_id": f"ALM-STORM3-{i:03d}",
            "timestamp": (base_time3 + t_offset).isoformat() + "Z",
            "node": node,
            "node_type": "UPF" if node == "UPF-02" else "CMG",
            "alarm_code": alarm_code,
            "alarm_name": f"{alarm_code.replace('_', ' ').title()} Alert",
            "severity": severity,
            "type": "Service",
            "description": f"PFCP control plane loss impact on {node}",
            "status": "ACTIVE"
        })

    # -------------------------------------------------------------
    # STORM 4: Physical Fiber Cut LINK-B (60 alarms, 16:00:00 - 16:05:00)
    # Root: LINK-B down -> UPF-01 and UPF-02 Packet Loss & Throughput Drop
    # -------------------------------------------------------------
    base_time4 = datetime(2026, 10, 8, 16, 0, 0)
    alarms.append({
        "alarm_id": "ALM-STORM4-001",
        "timestamp": base_time4.isoformat() + "Z",
        "node": "LINK-B",
        "node_type": "Transport",
        "alarm_code": "LINK_DOWN",
        "alarm_name": "Agra Edge Fiber Ring Break",
        "severity": "CRITICAL",
        "type": "Transport",
        "description": "Optical fiber cut detected on DWDM Span Agra-East Port 1/1/2",
        "status": "ACTIVE"
    })
    
    for i in range(2, 61):
        t_offset = timedelta(seconds=random.randint(5, 295))
        node = random.choice(["UPF-01", "UPF-02"])
        alarm_code = random.choice(["PACKET_LOSS_HIGH", "THROUGHPUT_DROP", "INTERFACE_ERRORS"])
        severity = random.choice(["CRITICAL", "MAJOR", "MINOR"])
        alarms.append({
            "alarm_id": f"ALM-STORM4-{i:03d}",
            "timestamp": (base_time4 + t_offset).isoformat() + "Z",
            "node": node,
            "node_type": "UPF",
            "alarm_code": alarm_code,
            "alarm_name": f"{alarm_code.replace('_', ' ').title()} Alert",
            "severity": severity,
            "type": "Transport" if "LOSS" in alarm_code else "Service",
            "description": f"Transport degradation secondary impact on {node}",
            "status": "ACTIVE"
        })

    # -------------------------------------------------------------
    # BACKGROUND NOISE ALARMS (~250 isolated alarms across 24h)
    # -------------------------------------------------------------
    start_day = datetime(2026, 10, 8, 0, 0, 0)
    nodes_all = ["LINK-A", "LINK-B", "CMG-01", "CMG-02", "CMG-03", "UPF-01", "UPF-02"]
    for i in range(1, 251):
        sec_offset = random.randint(0, 86400)
        t_stamp = start_day + timedelta(seconds=sec_offset)
        # Avoid storm windows
        if any(abs((t_stamp - st).total_seconds()) < 600 for st in [base_time, base_time2, base_time3, base_time4]):
            continue
        node = random.choice(nodes_all)
        node_type = "Transport" if "LINK" in node else ("CMG" if "CMG" in node else "UPF")
        alarm_code = random.choice(["FAN_WARNING", "TEMP_MINOR", "NTP_SYNC_WARN", "LOG_DISK_80"])
        alarms.append({
            "alarm_id": f"ALM-NOISE-{i:04d}",
            "timestamp": t_stamp.isoformat() + "Z",
            "node": node,
            "node_type": node_type,
            "alarm_code": alarm_code,
            "alarm_name": f"{alarm_code.replace('_', ' ').title()}",
            "severity": "WARNING" if "WARN" in alarm_code else "MINOR",
            "type": "Hardware" if "FAN" in alarm_code or "TEMP" in alarm_code else "System",
            "description": f"Routine system notification on {node}",
            "status": "ACTIVE"
        })

    df = pd.DataFrame(alarms)
    df.sort_values(by="timestamp", inplace=True)
    df.to_csv(settings.ALARMS_FILE, index=False)
    print(f"Generated {len(df)} synthetic alarms saved to {settings.ALARMS_FILE}")

def generate_kpi_data():
    records = []
    nodes = ["CMG-01", "CMG-02", "CMG-03", "UPF-01", "UPF-02"]
    kpis = ["cpu_utilization", "memory_utilization", "bgp_session_state", "throughput_gbps", "packet_loss_pct", "active_bearers"]
    
    start_time = datetime(2026, 10, 8, 0, 0, 0)
    num_intervals = 288  # 24 hours at 5-minute intervals
    
    for i in range(num_intervals):
        curr_time = start_time + timedelta(minutes=5 * i)
        time_str = curr_time.isoformat() + "Z"
        
        for node in nodes:
            # Baseline normal values
            cpu = random.uniform(15.0, 35.0)
            mem = random.uniform(30.0, 50.0)
            bgp = 1.0  # 1.0 = UP, 0.0 = DOWN
            thpt = random.uniform(80.0, 120.0)
            pkt_loss = random.uniform(0.0, 0.05)
            bearers = random.randint(450000, 550000)
            
            # Plant Anomaly 1 (10:00 - 10:15) Storm 1: LINK-A down -> CMG-02 BGP down, thpt drop
            if datetime(2026, 10, 8, 10, 0, 0) <= curr_time <= datetime(2026, 10, 8, 10, 15, 0):
                if node in ["CMG-02", "CMG-03"]:
                    bgp = 0.0 if node == "CMG-02" else 1.0
                    thpt = random.uniform(5.0, 20.0)
                    pkt_loss = random.uniform(2.5, 8.0)
                    
            # Plant Anomaly 2 (12:00 - 12:15) Storm 2: CMG-01 CPU/Memory spike
            if datetime(2026, 10, 8, 12, 0, 0) <= curr_time <= datetime(2026, 10, 8, 12, 15, 0):
                if node == "CMG-01":
                    cpu = random.uniform(96.0, 99.8)
                    mem = random.uniform(92.0, 97.5)
                elif node == "UPF-01":
                    bearers = random.randint(50000, 120000)
                    
            # Plant Anomaly 3 (14:00 - 14:15) Storm 3: CMG-03/UPF-02 PFCP failure
            if datetime(2026, 10, 8, 14, 0, 0) <= curr_time <= datetime(2026, 10, 8, 14, 15, 0):
                if node in ["CMG-03", "UPF-02"]:
                    bearers = random.randint(10000, 50000)
                    thpt = random.uniform(10.0, 30.0)
                    
            # Plant Anomaly 4 (16:00 - 16:15) Storm 4: LINK-B fiber cut affecting UPF-01 & UPF-02
            if datetime(2026, 10, 8, 16, 0, 0) <= curr_time <= datetime(2026, 10, 8, 16, 15, 0):
                if node in ["UPF-01", "UPF-02"]:
                    pkt_loss = random.uniform(15.0, 35.0)
                    thpt = random.uniform(2.0, 15.0)
            
            records.append({"timestamp": time_str, "node": node, "kpi_name": "cpu_utilization", "value": round(cpu, 2)})
            records.append({"timestamp": time_str, "node": node, "kpi_name": "memory_utilization", "value": round(mem, 2)})
            records.append({"timestamp": time_str, "node": node, "kpi_name": "bgp_session_state", "value": round(bgp, 2)})
            records.append({"timestamp": time_str, "node": node, "kpi_name": "throughput_gbps", "value": round(thpt, 2)})
            records.append({"timestamp": time_str, "node": node, "kpi_name": "packet_loss_pct", "value": round(pkt_loss, 4)})
            records.append({"timestamp": time_str, "node": node, "kpi_name": "active_bearers", "value": float(bearers)})

    df = pd.DataFrame(records)
    df.to_csv(settings.KPI_FILE, index=False)
    print(f"Generated {len(df)} KPI metric records saved to {settings.KPI_FILE}")

def generate_runbooks():
    settings.RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    runbooks = {
        "RB-01_Transport_Link_Down.md": """# Runbook: Physical Transport Link Down (LINK-A / LINK-B)

## 1. Overview
This runbook provides diagnostic and remediation steps when a physical fiber link or DWDM transport connection experiences Loss of Signal (LOS) or link down state.

## 2. Root Cause Analysis
- Physical optical fiber cut or transceiver failure on DWDM span.
- Router port failure or administrative shutdown.
- Upstream transport network provider outage.

## 3. Next Checks
- **Check 1**: Run `show router Base interface` on connected CMG/UPF nodes to verify operational status of physical ports.
- **Check 2**: Run `ping <neighbor_ip>` from CMG to neighbor node across the link.
- **Check 3**: Check optical transceiver RX power levels via `show port <port_id> optical-diagnostics`.
- **Check 4**: Verify BGP peer status via `show router bgp neighbor` to assess protocol cascade.

## 4. Remediation Steps
- Dispatch field optical fiber repair team to inspect fiber span.
- Clean optical connectors or replace SFP/QSFP transceiver.
- Failover traffic to secondary transport ring (LINK-B).
""",
        "RB-02_BGP_Peer_Down.md": """# Runbook: BGP Peer Session Down (CMG Nodes)

## 1. Overview
Triggered when a BGP session between Nokia CMG gateways or routers drops from Established to OpenSent/Idle.

## 2. Root Cause Analysis
- Underlying transport network failure (e.g. LINK-A down).
- TCP port 179 block or MTU mismatch.
- High CPU on CMG control plane preventing BGP keepalive handling.

## 3. Next Checks
- **Check 1**: Run `show router bgp neighbor` to check state and hold-time timer counters.
- **Check 2**: Run `ping <peer_ip>` to verify IP connectivity.
- **Check 3**: Run `show router interface` to verify underlying IP interface operational status.
- **Check 4**: Check CMG CPM CPU utilization via `show system cpu`.

## 4. Remediation Steps
- Resolve underlying link loss if link down alarm exists.
- Reset BGP session using `clear router bgp neighbor <peer_ip>`.
""",
        "RB-03_Service_Degradation.md": """# Runbook: Mobile Gateway Service Degradation

## 1. Overview
Indicates subscriber attach failures, bearer drops, or throughput degradation on Nokia CMG/UPF nodes.

## 2. Next Checks
- **Check 1**: Run `show mobile-gateway system` to inspect active session counts and CP-ISA card status.
- **Check 2**: Run `get_kpi(node, 'throughput_gbps', 15)` to verify user-plane bandwidth trends.
- **Check 3**: Verify PFCP association status between CMG and UPF using `show mobile-gateway pfcp peer`.

## 3. Remediation Steps
- Inspect upstream transport and BGP status.
- If CP-ISA card overload exists, rebalance APN traffic across standby ISAs.
""",
        "RB-04_CPU_Memory_Exhaustion.md": """# Runbook: CMG CPM/ISA High CPU and Memory Exhaustion

## 1. Overview
Covers high CPU (>95%) or memory usage on Control Plane Module (CPM) or Integrated Service Adapter (ISA) cards.

## 2. Diagnostics
- High GTP control message rate or signaling storm.
- Memory leak in routing process or subscriber table explosion.

## 3. Next Checks
- **Check 1**: Run `show system cpu` and `show system memory` on target node.
- **Check 2**: Run `get_kpi(node, 'cpu_utilization', 30)` to inspect rolling baseline deviation.
- **Check 3**: Inspect subscriber attach rate counters via `show mobile-gateway pdn-context`.
""",
        "RB-05_GTP_Path_Failure.md": """# Runbook: GTP Path Management Failure

## 1. Overview
Occurs when GTP-C or GTP-U echo request/response messages fail between SGW/PGW and external peers.

## 2. Next Checks
- **Check 1**: Verify GTP peer reachability via ping to peer IP.
- **Check 2**: Run `show mobile-gateway gtp statistics` to inspect GTP echo timeout count.
""",
        "RB-06_PFCP_Heartbeat_Failure.md": """# Runbook: PFCP Heartbeat Timeout (N4 / Sxa / Sxb)

## 1. Overview
PFCP heartbeat timeout between CMG (Control Plane) and UPF (User Plane).

## 2. Diagnostics
- Intermediate router packet drop on UDP port 8805.
- UPF node crash or freeze.

## 3. Next Checks
- **Check 1**: Run `show mobile-gateway pfcp peer` on CMG node.
- **Check 2**: Run `ping <upf_ip>` to verify UPF control interface reachability.
- **Check 3**: Check UPF system status via `show system summary`.
""",
        "RB-07_Bearer_Creation_Failure.md": """# Runbook: Bearer Creation Failure (UPF / SGW)

## 1. Overview
Subscribers fail to establish 4G/5G data sessions due to bearer setup rejects.

## 2. Next Checks
- **Check 1**: Run `get_kpi(node, 'active_bearers', 30)` to detect session drops.
- **Check 2**: Run `show mobile-gateway pdn-context statistics` for error cause codes.
""",
        "RB-08_Packet_Loss_High.md": """# Runbook: High User Plane Packet Loss

## 1. Overview
Excessive packet loss (>1%) detected on UPF user plane interfaces.

## 2. Next Checks
- **Check 1**: Run `show port ethernet statistics` for CRC errors and drops.
- **Check 2**: Run `get_kpi(node, 'packet_loss_pct', 15)` to confirm severity.
""",
        "RB-09_Throughput_Drop.md": """# Runbook: Data Plane Throughput Drop

## 1. Overview
Aggregate traffic throughput drops significantly below baseline.

## 2. Next Checks
- **Check 1**: Check transport interface bandwidth utilization.
- **Check 2**: Run `get_kpi(node, 'throughput_gbps', 15)` and compare against baseline.
""",
        "RB-10_Hardware_Fault.md": """# Runbook: Hardware Card and Chassis Faults

## 1. Overview
Covers fan module failure, power supply failure, or MDA card alarm.

## 2. Next Checks
- **Check 1**: Run `show chassis` to inspect hardware state and environmental sensors.
- **Check 2**: Contact hardware vendor support if component replacement is needed.
"""
    }
    
    for filename, content in runbooks.items():
        filepath = settings.RUNBOOKS_DIR / filename
        with open(filepath, "w") as f:
            f.write(content.strip())
    print(f"Generated 10 runbooks in {settings.RUNBOOKS_DIR}")

def generate_past_incidents():
    settings.PAST_INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    incidents = {
        "INC-2025-0101_Transport_Link_Failure.md": """# Incident Summary: INC-2025-0101
**Title**: Primary Transport Fiber Cut on LINK-A causing BGP Cascade
**Date**: 2025-06-15
**Nodes Affected**: LINK-A, CMG-02, CMG-03
**Root Cause**: Fiber optic cut by road construction on main trunk span Agra-Core.
**Symptoms**: 42 alarms including LINK_DOWN, BGP_PEER_DOWN, and CMG Service Degradation.
**Resolution**: Traffic re-routed to secondary fiber ring LINK-B. Optical fiber spliced by field engineering in 3.5 hours.
""",
        "INC-2025-0102_BGP_Peer_Flap.md": """# Incident Summary: INC-2025-0102
**Title**: BGP Peer Session Flapping on CMG-02
**Date**: 2025-07-20
**Nodes Affected**: CMG-02
**Root Cause**: Transceiver SFP degradation causing intermittent optical packet drops.
**Symptoms**: BGP_PEER_DOWN followed by automatic reconnect every 10 minutes.
**Resolution**: Replaced optical SFP module on CMG-02 port 1/1/1.
""",
        "INC-2025-0103_CMG_CPU_Spike.md": """# Incident Summary: INC-2025-0103
**Title**: Control Plane CPU Exhaustion on CMG-01
**Date**: 2025-08-11
**Nodes Affected**: CMG-01, UPF-01
**Root Cause**: High volume signalling storm triggered by massive smartphone re-attaches post power outage.
**Symptoms**: CPU_HIGH alarm on CMG-01, GTP path failures on UPF-01.
**Resolution**: Rate-limited incoming GTP attach requests and added secondary CP-ISA card.
""",
        "INC-2025-0104_PFCP_Timeout.md": """# Incident Summary: INC-2025-0104
**Title**: PFCP Association Loss between CMG-03 and UPF-02
**Date**: 2025-09-02
**Nodes Affected**: CMG-03, UPF-02
**Root Cause**: Firewall UDP port 8805 packet buffer overflow.
**Symptoms**: PFCP_HEARTBEAT_FAIL and bearer setup failure on UPF-02.
**Resolution**: Updated firewall UDP buffer sizing and restarted PFCP daemon.
""",
        "INC-2025-0105_Fiber_Cut_LINK_B.md": """# Incident Summary: INC-2025-0105
**Title**: DWDM Span Break on LINK-B Ring
**Date**: 2025-09-28
**Nodes Affected**: LINK-B, UPF-01, UPF-02
**Root Cause**: Severe storm damaged overhead fiber cable.
**Symptoms**: High packet loss and throughput drop on UPF nodes.
**Resolution**: Switched UPF traffic path to core MPLS network.
""",
        "INC-2025-0106_UPF_Bearer_Drop.md": """# Incident Summary: INC-2025-0106
**Title**: Massive Bearer Drop on UPF-01
**Date**: 2025-10-05
**Nodes Affected**: UPF-01
**Root Cause**: Software memory corruption in UPF forwarding engine.
**Symptoms**: Sudden loss of 300,000 active sessions.
**Resolution**: Performed soft reboot of UPF-01 forwarding card.
""",
        "INC-2025-0107_GTP_Path_Restarts.md": """# Incident Summary: INC-2025-0107
**Title**: GTP Path Management Restarts on CMG-01
**Date**: 2025-11-12
**Nodes Affected**: CMG-01
**Root Cause**: Misconfigured GTP keepalive timer (set to 5s instead of 30s).
**Symptoms**: Intermittent GTP_PATH_FAIL warnings.
**Resolution**: Restored standard GTP keepalive timer value in config.
""",
        "INC-2025-0108_Memory_Leak_CMG.md": """# Incident Summary: INC-2025-0108
**Title**: Slow Memory Leak on CPM Slot 1
**Date**: 2025-12-01
**Nodes Affected**: CMG-02
**Root Cause**: Memory leak in logging daemon after 90 days uptime.
**Symptoms**: MEMORY_HIGH warning growing gradually.
**Resolution**: Applied software patch R26.7.R1 and restarted logging daemon.
""",
        "INC-2025-0109_SGW_Interface_Flap.md": """# Incident Summary: INC-2025-0109
**Title**: S1-U Interface Port Flap on UPF-02
**Date**: 2026-01-14
**Nodes Affected**: UPF-02
**Root Cause**: Loose ethernet patch cable on switch port.
**Symptoms**: Interface error counts rising rapidly.
**Resolution**: Re-seated patch cable securely.
""",
        "INC-2025-0110_Optical_Transceiver_Fault.md": """# Incident Summary: INC-2025-0110
**Title**: Transceiver Power Fault on LINK-A
**Date**: 2026-02-22
**Nodes Affected**: LINK-A
**Root Cause**: Laser aging on 100G QSFP28 transceiver.
**Symptoms**: Optical signal attenuation and framing errors.
**Resolution**: Replaced QSFP28 transceiver.
"""
    }
    
    for filename, content in incidents.items():
        filepath = settings.PAST_INCIDENTS_DIR / filename
        with open(filepath, "w") as f:
            f.write(content.strip())
    print(f"Generated 10 past incident summaries in {settings.PAST_INCIDENTS_DIR}")

if __name__ == "__main__":
    generate_topology()
    generate_alarms()
    generate_kpi_data()
    generate_runbooks()
    generate_past_incidents()
    print("All synthetic datasets generated successfully!")
