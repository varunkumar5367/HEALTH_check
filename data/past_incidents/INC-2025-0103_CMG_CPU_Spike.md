# Incident Summary: INC-2025-0103
**Title**: Control Plane CPU Exhaustion on CMG-01
**Date**: 2025-08-11
**Nodes Affected**: CMG-01, UPF-01
**Root Cause**: High volume signalling storm triggered by massive smartphone re-attaches post power outage.
**Symptoms**: CPU_HIGH alarm on CMG-01, GTP path failures on UPF-01.
**Resolution**: Rate-limited incoming GTP attach requests and added secondary CP-ISA card.