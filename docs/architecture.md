# Architecture & Design Overview: Network Triage Agent

```mermaid
flowchart TD
    subgraph Data Layer
        A1[Synthetic Alarms ~500] --> INGEST[Data Loaders & Normalisers]
        A2[KPI CSVs 5 Nodes] --> INGEST
        A3[Topology JSON NetworkX] --> INGEST
        A4[Nokia 3GPP PM XML Gz] --> INGEST
        A5[CMG Excel Workbook] --> INGEST
    end

    subgraph Correlation & Diagnostics
        INGEST --> CORR[Sliding Window & Topology Correlator]
        CORR --> INC[Incident Objects]
        INC --> RANK[5-Criteria Probable Root Ranker]
        INC --> KPI_ANOM[Direction-Aware Z-score Anomaly Checker]
    end

    subgraph Knowledge & RAG
        R1[10 Runbook Pages] --> RAG_IDX[Hybrid Vector Indexer TF-IDF / Embeddings]
        R2[10 Past Incident Summaries] --> RAG_IDX
        RAG_IDX --> RET[RAG Retriever - Mandatory Citations]
    end

    subgraph Agent Loop & Guardrails
        RANK --> AGENT[Triage Agent Loop]
        KPI_ANOM --> AGENT
        RET --> AGENT
        AGENT --> OBS[1. Observe Alarms & Topology]
        OBS --> HYP[2. Hypothesise Root Cause]
        HYP --> ACT[3. Act: Read-Only Tools ping/status/kpi]
        ACT --> EVAL[4. Evaluate Guardrails MAX_STEPS / Confidence]
        EVAL --> CONC[5. Conclude & Draft Ticket]
    end

    subgraph Presentation & API
        AGENT --> REST[FastAPI REST API /docs]
        AGENT --> UI[Streamlit Interactive Dashboard]
        UI --> HITL[Human NOC Engineer Confirmation Gate]
        HITL --> NOTIFY[POST /notify Webhook Teams/Email]
        HITL --> TICKET[POST /ticket Mock ITSM Ticket]
    end
```

## Key Architectural Principles
1. **Strict Read-Only Guarantee**: Agent tools only inspect state (`ping`, `get_kpi`, `show_status`, `topology_neighbors`, `search_runbook`, `search_past_incidents`). No network mutations occur.
2. **Deterministic & Resilient Pipeline**: Works 100% offline using deterministic graph & TF-IDF algorithms even if external LLM/API endpoints are unreachable.
3. **Mandatory Citation Enforcement**: Every suggested next check directly references its originating runbook section (`runbook_name#section_heading`).
4. **Human-in-the-Loop Confirmation Gate**: Actions like Teams/Email notifications or ITSM ticket submission require explicit NOC engineer checkbox confirmation.
