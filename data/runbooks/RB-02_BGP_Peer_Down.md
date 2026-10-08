# Runbook: BGP Peer Session Down (CMG Nodes)

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