# Runbook: High User Plane Packet Loss

## 1. Overview
Excessive packet loss (>1%) detected on UPF user plane interfaces.

## 2. Next Checks
- **Check 1**: Run `show port ethernet statistics` for CRC errors and drops.
- **Check 2**: Run `get_kpi(node, 'packet_loss_pct', 15)` to confirm severity.