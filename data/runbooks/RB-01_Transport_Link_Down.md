# Runbook: Physical Transport Link Down (LINK-A / LINK-B)

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