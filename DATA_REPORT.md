# DATA_REPORT.md: Workspace & Raw Data Inventory

## Executive Summary
This report presents the inventory, schema analysis, and row counts of all workspace files discovered for **Problem Statement 06: Network Health-Check and Alarm Triage Agent**.

---

## 1. Raw File Inventory

| Path / File Name | File Size | Format / Type | Purpose & Description |
| :--- | :--- | :--- | :--- |
| `PS06_Health_Check_and_Alarm_Triage_Agent.pdf` | ~204 KB | PDF | Official Problem Statement specification and rules. |
| `CMG_KPI_MONITORING_TEMPLATE_V1.2...xlsx` | ~41 KB | XLSX | Nokia CMG KPI monitoring workbook containing formulas, thresholds, and commercial rules. |
| `7750_SR_MG_and_CMG_Software_Release_Notes...pdf` | ~2.17 MB | PDF | Software release notes for Nokia 7750 SR MG & CMG R26.7.R1. |
| `KPI-KCI/*.xml.gz` (19 files) | ~10 KB - ~1.3 MB | 3GPP PM XML (Gzip) | Real Nokia Performance Monitoring XML files with `measObjLdn`, 3GPP counter definitions, and `suspect` flags. |
| `Supported Commands/*.txt` (3 files) | ~9.7 KB - ~12.6 KB | Text | Operational health-check commands for CPF, UPF-1, and UPF-2 nodes. |
| `Alarms and Logs Outputs/*` | ~300 KB - ~5.3 MB | Text / Zip | Pre- and post-health checkup log outputs from CPF, UPF-01, and UPF-02 nodes. |
| `Requirement.txt` | 201 bytes | Text | High-level requirements note. |

---

## 2. Inventory Status vs. Specification Expectations

| Expected Core Data Item | Status in Raw Directory | Resolution / Action |
| :--- | :--- | :--- |
| **~500 Synthetic Alarms with 4 Planted Incident Storms** | **Not found** | Synthesized into `data/alarms.csv` / `data/alarms.json` per PS06 spec, including the exact sample scenario (LINK-A down, BGP peer down on CMG-02, service degradation on CMG-02/CMG-03). |
| **KPI CSVs for 5 Nodes** | **Not found** | Generated into `data/kpi_data.csv` covering 5 nodes (CMG-01, CMG-02, CMG-03, UPF-01, UPF-02) with 5-minute interval baseline & anomaly data. |
| **Topology JSON of Node Links** | **Not found** | Defined in `data/topology.json` representing network adjacency and dependency graph across the 5 nodes and transport links. |
| **10 Runbook Pages** | **Not found** | Authored in `data/runbooks/` covering Transport, BGP, SGW/PGW, PFCP, CPU, Memory, and Interface triage procedures with cited sections. |
| **10 Past-Incident Summaries** | **Not found** | Created in `data/past_incidents/` containing historical incident reports with root causes and resolutions for RAG similarity match. |
| **Nokia 3GPP PM XML Files** | **Found (19 files)** | Parsed via streaming `xml.etree.ElementTree` with `gzip` as live KPI enrichment & counter verification. |
| **Supported Commands List** | **Found (3 files)** | Parsed and exposed via agent CLI tools and health check REST endpoints. |
| **CMG KPI Monitoring Workbook** | **Found (1 file)** | Parsed via `openpyxl` to extract KPI baseline formulas and capacity thresholds. |

---

## 3. Data Schemas & Structure

### A. Synthetic Alarms Schema (`data/alarms.csv`)
- `alarm_id` (str): Unique identifier (e.g., `ALM-20261008-001`)
- `timestamp` (str): ISO 8601 timestamp (e.g., `2026-10-08T10:00:00Z`)
- `node` (str): Node name (e.g., `LINK-A`, `CMG-01`, `CMG-02`, `CMG-03`, `UPF-01`, `UPF-02`)
- `node_type` (str): Type of node (`Transport`, `CMG`, `UPF`, `Router`)
- `alarm_code` (str): Code identifier (e.g., `LINK_DOWN`, `BGP_PEER_DOWN`, `SERVICE_DEGRADED`, `CPU_HIGH`)
- `alarm_name` (str): Human-readable name
- `severity` (str): `CRITICAL`, `MAJOR`, `MINOR`, `WARNING`, `CLEAR`
- `type` (str): Category (`Transport`, `Protocol`, `Service`, `Hardware`, `Capacity`)
- `description` (str): Detailed text explanation
- `status` (str): `ACTIVE`, `CLEARED`

### B. Topology Graph Schema (`data/topology.json`)
- `nodes`: List of dicts `{"id": "CMG-02", "type": "CMG", "site": "Agra"}`
- `edges`: List of dicts `{"source": "LINK-A", "target": "CMG-02", "link_type": "Transport"}`

### C. KPI Timeseries Schema (`data/kpi_data.csv`)
- `timestamp` (str): ISO 8601 timestamp
- `node` (str): Node identifier
- `kpi_name` (str): Metric name (e.g., `cpu_utilization`, `bgp_session_state`, `throughput_gbps`, `packet_loss_pct`)
- `value` (float): Numeric value

### D. Nokia 3GPP PM XML Schema (`KPI-KCI/*.xml.gz`)
- Root: `measCollecFile` (3GPP TS 32.435)
- Header: `fileSender` localDn, `beginTime`, `endTime`
- Data: `measData` -> `managedElement`, `measInfo` (`measInfoId`) -> `measTypes`, `measValue` (`measObjLdn`, `suspect`, `r` results)

---

## 4. Execution Plan Adaptation
1. Build `app/ingest/generate_data.py` to produce standard synthetic datasets matching all 4 planted storms and the sample scenario.
2. Build `app/ingest/nokia_xml_parser.py` and `app/ingest/excel_parser.py` to ingest real Nokia PM XMLs and CMG KPI thresholds as enrichment.
3. Complete Phases 1 through 9 step-by-step with automated verification tests for every phase.
