# Incident Summary: INC-2025-0107
**Title**: GTP Path Management Restarts on CMG-01
**Date**: 2025-11-12
**Nodes Affected**: CMG-01
**Root Cause**: Misconfigured GTP keepalive timer (set to 5s instead of 30s).
**Symptoms**: Intermittent GTP_PATH_FAIL warnings.
**Resolution**: Restored standard GTP keepalive timer value in config.