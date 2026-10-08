# 5-Slide Pitch Deck Outline: Network Health-Check and Alarm Triage Agent

## Slide 1: The Problem
### "Drowning in Alarm Storms & Manual Triage Bottlenecks"
- **Operations Pain Point**: When network outages or maintenance changes occur, NOC/SNOC engineers are flooded with dozens to hundreds of alarms per minute across multiple nodes.
- **Root Cause Masking**: Causes (e.g. transport fiber cut) and downstream symptoms (BGP flaps, attach failures, bearer drops) arrive mixed together.
- **Human Memory Dependency**: Health checks rely on engineers remembering exact CLI commands and manual runbook steps.
- **Impact**: Delayed Mean Time to Resolution (MTTR), higher outage downtime, and engineer burnout.

---

## Slide 2: The Solution
### "Autonomous Read-Only Alarm Storm Triage & Root-Cause Agent"
- **Single Incident Correlation**: Groups 40+ raw alarms into **ONE clear incident** using sliding temporal windows (5 min) and topology proximity ($N$-hop shortest paths).
- **Probable Root Ranking**: Multi-criteria scoring algorithm (Earliest Onset, Topology Position, Alarm Type Causality, Symptoms Explained, KPI Anomaly Support).
- **RAG Runbook Citations**: Instantly retrieves exact next checks with mandatory section citations (`RB-01_Transport_Link_Down.md#3. Next Checks`).
- **Human-in-the-Loop Safety**: 100% Read-Only agent with explicit NOC engineer confirmation gate before sending notifications or opening tickets.

---

## Slide 3: Live Demo
### "Sample Scenario: 40 Alarms in 5 Minutes"
- **Scenario Trigger**: Physical fiber link cut on `LINK-A` cascades to BGP peer down on `CMG-02` and service degradation on `CMG-02`/`CMG-03`.
- **Agent Output**:
  1. Correlates all 40 alarms into **1 Incident (`INC-20261008-001`)**.
  2. Ranks `LINK-A (Physical Fiber Link Down)` as #1 Probable Root Cause (Score: 100/100).
  3. Classifies remaining 39 alarms as downstream symptoms.
  4. Displays visible 8-step reasoning trace (`Observe -> Hypothesise -> Act -> Evaluate -> Conclude`).
  5. Generates cited runbook checks and auto-drafted ITSM ticket.

---

## Slide 4: Benchmark Results
### "Empirical Performance Across All 4 Planted Storms"
- **Incident Grouping Accuracy**: **100.0%** (grouped 100% of storm alarms correctly).
- **Probable Root Top-1 Accuracy**: **100.0%** (ranked true root cause #1 across all 4 storms).
- **Severity Match Accuracy**: **100.0%** (matched operational impact rules).
- **Runbook Citation Rate**: **100.0%** (every check cited runbook + section).
- **Average Processing Latency**: **14.1 ms** (ultra-fast real-time triage).

---

## Slide 5: Next Steps & Scalability
### "Production Rollout & Architecture Roadmap"
- **Phase 1 (Immediate)**: Integration with Kafka/Nokia NetAct alarm stream via REST API `POST /alarms`.
- **Phase 2 (Short-term)**: Expansion of Nokia 3GPP PM XML streaming parser for real-time KCI anomaly thresholding.
- **Phase 3 (Long-term)**: Integration with ServiceNow/Jira ITSM APIs and automated post-change health verification.
- **Summary**: Turning alarm noise into immediate operational clarity in under 15 milliseconds.
