# Runbook: Mobile Gateway Service Degradation

## 1. Overview
Indicates subscriber attach failures, bearer drops, or throughput degradation on Nokia CMG/UPF nodes.

## 2. Next Checks
- **Check 1**: Run `show mobile-gateway system` to inspect active session counts and CP-ISA card status.
- **Check 2**: Run `get_kpi(node, 'throughput_gbps', 15)` to verify user-plane bandwidth trends.
- **Check 3**: Verify PFCP association status between CMG and UPF using `show mobile-gateway pfcp peer`.

## 3. Remediation Steps
- Inspect upstream transport and BGP status.
- If CP-ISA card overload exists, rebalance APN traffic across standby ISAs.