# Incident Summary: INC-2025-0108
**Title**: Slow Memory Leak on CPM Slot 1
**Date**: 2025-12-01
**Nodes Affected**: CMG-02
**Root Cause**: Memory leak in logging daemon after 90 days uptime.
**Symptoms**: MEMORY_HIGH warning growing gradually.
**Resolution**: Applied software patch R26.7.R1 and restarted logging daemon.