# Runbook: GTP Path Management Failure

## 1. Overview
Occurs when GTP-C or GTP-U echo request/response messages fail between SGW/PGW and external peers.

## 2. Next Checks
- **Check 1**: Verify GTP peer reachability via ping to peer IP.
- **Check 2**: Run `show mobile-gateway gtp statistics` to inspect GTP echo timeout count.