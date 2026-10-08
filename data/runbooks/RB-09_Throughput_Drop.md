# Runbook: Data Plane Throughput Drop

## 1. Overview
Aggregate traffic throughput drops significantly below baseline.

## 2. Next Checks
- **Check 1**: Check transport interface bandwidth utilization.
- **Check 2**: Run `get_kpi(node, 'throughput_gbps', 15)` and compare against baseline.