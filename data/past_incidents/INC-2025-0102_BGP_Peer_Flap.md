# Incident Summary: INC-2025-0102
**Title**: BGP Peer Session Flapping on CMG-02
**Date**: 2025-07-20
**Nodes Affected**: CMG-02
**Root Cause**: Transceiver SFP degradation causing intermittent optical packet drops.
**Symptoms**: BGP_PEER_DOWN followed by automatic reconnect every 10 minutes.
**Resolution**: Replaced optical SFP module on CMG-02 port 1/1/1.