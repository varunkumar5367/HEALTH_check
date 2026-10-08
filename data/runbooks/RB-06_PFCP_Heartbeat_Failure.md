# Runbook: PFCP Heartbeat Timeout (N4 / Sxa / Sxb)

## 1. Overview
PFCP heartbeat timeout between CMG (Control Plane) and UPF (User Plane).

## 2. Diagnostics
- Intermediate router packet drop on UDP port 8805.
- UPF node crash or freeze.

## 3. Next Checks
- **Check 1**: Run `show mobile-gateway pfcp peer` on CMG node.
- **Check 2**: Run `ping <upf_ip>` to verify UPF control interface reachability.
- **Check 3**: Check UPF system status via `show system summary`.