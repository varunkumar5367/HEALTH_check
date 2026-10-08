# Runbook: Bearer Creation Failure (UPF / SGW)

## 1. Overview
Subscribers fail to establish 4G/5G data sessions due to bearer setup rejects.

## 2. Next Checks
- **Check 1**: Run `get_kpi(node, 'active_bearers', 30)` to detect session drops.
- **Check 2**: Run `show mobile-gateway pdn-context statistics` for error cause codes.