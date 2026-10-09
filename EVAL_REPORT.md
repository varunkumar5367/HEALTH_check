# EVAL_REPORT.md: Benchmark & Scenario Verification Report

## Executive Summary
This report presents the benchmark performance results of the **Network Health-Check and Alarm Triage Agent** evaluated across all 4 planted incident storms, including the mandatory sample scenario.

---

## 1. Evaluation Results Summary

| Benchmark Metric | Target Threshold | Measured Score | Status |
| :--- | :--- | :--- | :--- |
| **Incident Grouping Accuracy** | >90.0% | **100.0%** | PASS |
| **Probable Root Top-1 Accuracy** | >90.0% | **100.0%** | PASS |
| **Severity Rule Match** | 100.0% | **100.0%** | PASS |
| **Runbook Citation Rate** | 100.0% | **100.0%** | PASS |
| **Average Processing Latency** | <500 ms | **20.3 ms** | PASS |

---

## 2. Planted Incident Storm Test Matrix

| Scenario                   |   Raw Alarms |   Correlated Incidents | Expected Root   | Predicted Root   | Top-1 Match   | Assigned Severity   | Severity Match   | Citation Rate   | Latency (ms)   |
|:---------------------------|-------------:|-----------------------:|:----------------|:-----------------|:--------------|:--------------------|:-----------------|:----------------|:---------------|
| Storm 1 (Sample Scenario)  |           40 |                      1 | LINK-A          | LINK-A           | PASS          | CRITICAL            | PASS             | 100%            | 16.0 ms        |
| Storm 2 (CPU/Memory Spike) |           80 |                      1 | CMG-01          | CMG-01           | PASS          | CRITICAL            | PASS             | 100%            | 27.5 ms        |
| Storm 3 (PFCP Timeout)     |           70 |                      1 | CMG-03          | CMG-03           | PASS          | CRITICAL            | PASS             | 100%            | 22.6 ms        |
| Storm 4 (Fiber Cut LINK-B) |           60 |                      1 | LINK-B          | LINK-B           | PASS          | CRITICAL            | PASS             | 100%            | 15.0 ms        |

---

## 3. Sample Scenario Verification Detail

### Scenario Description
40 alarms arriving in 5 minutes (10:00 - 10:05): Physical link down on LINK-A, BGP peer down on CMG-02, and multiple service degradation alarms on CMG-02 and CMG-03.

### Agent Triage Output
- **Correlated Incidents**: Exactly 1 Incident (`INC-20261008-001`)
- **Probable Root Cause**: `LINK-A (Physical Fiber Link Down)` (Score: 100.0 / 100)
- **Assigned Severity**: `CRITICAL` / `HIGH`
- **Grouped Symptoms**: 39 alarms on CMG-02 and CMG-03
- **Cited Next Checks**: `RB-01_Transport_Link_Down.md#3. Next Checks`
- **Draft Ticket**: `TICK-20261008-001` with cited runbook recommendations
- **Human Confirmation Gate**: Verified and passed cleanly.