# 📡 Network Health-Check and Alarm Triage Agent (PS06)

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-orange.svg)](https://streamlit.io/)
[![pytest](https://img.shields.io/badge/pytest-passing-brightgreen.svg)](https://docs.pytest.org/)

An autonomous, **100% Read-Only Agentic AI System** built for **Problem Statement 06 (AI Automation Hackathon)**. It ingests raw network alarms, correlates alarm storms into single incidents, identifies probable root causes, checks directional KPI anomalies, retrieves section-cited runbooks, and outputs triage summaries with draft tickets and human-in-the-loop confirmation gates.

---

## 🌟 Key Capabilities
1. **Alarm Storm Correlation**: Reduces dozens/hundreds of raw alarms into discrete incident objects using a 5-minute sliding window and NetworkX topology proximity ($N$-hop shortest paths).
2. **Probable Root Cause Ranking**: Scores candidate nodes across 5 criteria (Earliest Onset, Topology Upstream Position, Alarm Type Causality, Symptoms Explained, KPI Anomaly Support).
3. **Direction-Aware KPI Anomaly Detection**: Calculates rolling baselines and directional Z-scores (high CPU/loss is bad, low BGP state is bad, throughput drops are flagged).
4. **Section-Cited RAG Retrieval**: Searches runbooks and past incidents with mandatory section citations (`runbook_name#section_heading`).
5. **Visible Reasoning Trace**: Logs the full 8-step agent loop (`Observe -> Hypothesise -> Act -> Evaluate -> Conclude`).
6. **Human-in-the-Loop Confirmation Gate**: Read-only safety guarantee. Notification webhooks and ITSM tickets require explicit NOC engineer validation before execution.

---

## 📁 Repository Structure
```
├── app/
│   ├── api/          # FastAPI REST API routes (/alarms, /triage/{id}, /incidents, /notify, /ticket, /tools/*)
│   ├── ingest/       # Data loaders, schema definitions, Nokia 3GPP PM XML parser, Excel threshold parser, generator
│   ├── correlation/  # Sliding window correlation engine & probable root ranking algorithm
│   ├── kpi/          # Rolling baseline and direction-aware Z-score anomaly detector
│   ├── agent/        # Read-only tool registry and 8-step Triage Agent Loop with guardrails
│   ├── rag/          # Hybrid Vector Indexer & Retriever enforcing mandatory section citations
│   ├── notify/       # Notification & ticket dispatch handlers
│   └── config.py     # Central application configuration
├── ui/
│   └── app.py        # Streamlit interactive dashboard
├── tests/            # Automated unit & integration tests (21 tests, 100% passing)
├── eval/
│   evaluate.py   # Benchmark evaluation script for all 4 planted storms
├── docs/
│   ├── architecture.md # Architectural workflow diagram (Mermaid)
│   └── pitch.md        # 5-Slide Pitch Deck outline
├── data/             # Synthetic datasets (alarms.csv, topology.json, kpi_data.csv, runbooks/, past_incidents/)
├── raw_data/         # Original PS06 dataset files (Nokia XMLs, CMG workbook, logs)
├── DATA_REPORT.md    # Workspace data inventory report
├── EVAL_REPORT.md    # Benchmark evaluation results table
├── run_app.py        # Single launch runner script
└── README.md         # Documentation
```

---

## 🚀 Quick Start & One-Command Run

### 1. Prerequisites
- Python 3.11 or 3.12
- Required packages: `fastapi`, `streamlit`, `pandas`, `networkx`, `scikit-learn`, `pydantic`, `pytest`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Or install directly: `pip install fastapi uvicorn streamlit pandas networkx scikit-learn pytest openpyxl`)*

### 3. Launch the Application (FastAPI REST API + Streamlit Dashboard)
Run the single runner script:
```bash
python run_app.py
```
- **Streamlit Dashboard**: [http://localhost:8501](http://localhost:8501)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Automated Tests & Evaluation

### Run Unit & Integration Tests (21 tests)
```bash
pytest
```

### Run Benchmark Evaluation Across All 4 Planted Storms
```bash
python -m eval.evaluate
```
*Generates `EVAL_REPORT.md` with full accuracy metrics.*

---

## 📊 Benchmark Evaluation Summary (`EVAL_REPORT.md`)

| Benchmark Metric | Target Threshold | Measured Score | Status |
| :--- | :--- | :--- | :--- |
| **Incident Grouping Accuracy** | >90.0% | **100.0%** | ✅ PASS |
| **Probable Root Top-1 Accuracy** | >90.0% | **100.0%** | ✅ PASS |
| **Severity Rule Match** | 100.0% | **100.0%** | ✅ PASS |
| **Runbook Citation Rate** | 100.0% | **100.0%** | ✅ PASS |
| **Average Processing Latency** | <500 ms | **14.1 ms** | ✅ PASS |

---

## 🎯 Step-by-Step Demo Guide (Sample Scenario)

1. Open the Streamlit Dashboard at `http://localhost:8501`.
2. In the sidebar dropdown **Select Incident Storm Scenario**, choose **"Storm 1: Sample Scenario (LINK-A Fiber Down -> BGP Down -> CMG Degradation)"**.
3. Observe that **40 alarms** arriving within 5 minutes are grouped into **1 Incident (`INC-20261008-001`)**.
4. Examine the **Triage Summary**:
   - **Probable Root Cause**: `LINK-A (Physical Fiber Link Down)`
   - **Assigned Severity**: `CRITICAL`
   - **Confidence Score**: `95.0%`
5. Click through the interactive tabs:
   - **📊 Alarms & Symptoms**: Inspect root cause alarm vs 39 grouped symptom alarms on `CMG-02`/`CMG-03`.
   - **🌐 Topology Graph**: View node dependency connections.
   - **📈 KPI Baseline & Anomalies**: Inspect BGP state drop to 0 on `CMG-02`.
   - **🧠 Agent Reasoning Trace**: Review the 8-step `Observe -> Hypothesise -> Act -> Evaluate -> Conclude` trace.
   - **📚 Cited Runbook Checks**: Verify mandatory citations (`RB-01_Transport_Link_Down.md#3. Next Checks`).
   - **🎫 Draft Ticket & Action**: Notice the NOC Engineer confirmation checkbox gate before clicking **Send Teams Notification** or **Create Ticket**.

---

## 🛠️ REST API Usage Examples

### 1. List Correlated Incidents
```bash
curl -X GET "http://localhost:8000/incidents"
```

### 2. Get Incident Triage Details
```bash
curl -X GET "http://localhost:8000/triage/INC-20261008-001"
```

### 3. Ingest Batch Alarms
```bash
curl -X POST "http://localhost:8000/alarms" \
     -H "Content-Type: application/json" \
     -d '[{"alarm_id":"ALM-999","timestamp":"2026-10-08T10:00:00Z","node":"LINK-A","node_type":"Transport","alarm_code":"LINK_DOWN","alarm_name":"Fiber Cut","severity":"CRITICAL","type":"Transport","description":"Loss of signal","status":"ACTIVE"}]'
```

### 4. Send Webhook Notification (Mock)
```bash
curl -X POST "http://localhost:8000/notify" \
     -H "Content-Type: application/json" \
     -d '{"incident_id":"INC-20261008-001","channel":"Teams","recipient":"noc-alerts@telco.com","message":"Triage complete for INC-20261008-001"}'
```

---

## 📌 Implementation Status & Design Rationale

| Feature Module | Implementation Status | Design Choice & Rationale |
| :--- | :--- | :--- |
| **Ingestion & Normalisation** | ✅ Fully Functional | Normalized schemas across alarms, KPIs, and topology graph. Includes Nokia 3GPP PM XML streaming parser and CMG Excel threshold loader. |
| **Incident Correlation** | ✅ Fully Functional | Sliding temporal window (5 min) + NetworkX topology proximity. Fast and deterministic. |
| **Probable Root Cause Ranking** | ✅ Fully Functional | 5-criteria weighted scoring algorithm (Max 100 pts) evaluating onset, topology position, causality, and symptoms. |
| **KPI Anomaly Detector** | ✅ Fully Functional | Direction-aware rolling baseline and Z-score anomaly detector. |
| **RAG Indexer & Retriever** | ✅ Fully Functional | TF-IDF & Cosine Similarity vector index delivering <5ms response times and 100% offline determinism with mandatory section citations. |
| **Agent Loop & Guardrails** | ✅ Fully Functional | 8-step reasoning loop with `MAX_STEPS` guardrail, confidence thresholding, and escalation handover. |
| **REST API** | ✅ Fully Functional | FastAPI app with complete Pydantic request models, Swagger OpenAPI docs, and diagnostic tool REST endpoints. |
| **Streamlit Dashboard** | ✅ Fully Functional | Interactive UI featuring scenario presets, reasoning trace, KPI charts, and human confirmation gates. |
| **External LLM Dependency** | 🔄 Mocked / Local Fallback | The system operates deterministically using template-based synthesis and local ranking rules so it functions 100% reliably even if Ollama/LLM endpoints are unavailable. |
