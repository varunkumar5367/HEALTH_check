# Runbook: CMG CPM/ISA High CPU and Memory Exhaustion

## 1. Overview
Covers high CPU (>95%) or memory usage on Control Plane Module (CPM) or Integrated Service Adapter (ISA) cards.

## 2. Diagnostics
- High GTP control message rate or signaling storm.
- Memory leak in routing process or subscriber table explosion.

## 3. Next Checks
- **Check 1**: Run `show system cpu` and `show system memory` on target node.
- **Check 2**: Run `get_kpi(node, 'cpu_utilization', 30)` to inspect rolling baseline deviation.
- **Check 3**: Inspect subscriber attach rate counters via `show mobile-gateway pdn-context`.