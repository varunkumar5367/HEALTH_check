# Incident Summary: INC-2025-0104
**Title**: PFCP Association Loss between CMG-03 and UPF-02
**Date**: 2025-09-02
**Nodes Affected**: CMG-03, UPF-02
**Root Cause**: Firewall UDP port 8805 packet buffer overflow.
**Symptoms**: PFCP_HEARTBEAT_FAIL and bearer setup failure on UPF-02.
**Resolution**: Updated firewall UDP buffer sizing and restarted PFCP daemon.