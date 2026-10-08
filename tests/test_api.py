import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["alarms_loaded"] > 100

def test_api_incidents_list():
    res = client.get("/incidents")
    assert res.status_code == 200
    data = res.json()
    assert data["total_incidents"] > 0
    assert "incidents" in data

def test_api_triage_by_id():
    # Get first incident ID
    res_list = client.get("/incidents")
    inc_id = res_list.json()["incidents"][0]["id"]
    
    res_triage = client.get(f"/triage/{inc_id}")
    assert res_triage.status_code == 200
    data = res_triage.json()
    assert "probable_root" in data
    assert "severity" in data
    assert "reasoning_trace" in data

def test_api_notify_and_ticket():
    # Test Notify
    notif_payload = {
        "incident_id": "INC-20261008-001",
        "channel": "Teams",
        "recipient": "noc-test@telco.com",
        "message": "Test notification alert"
    }
    res_notif = client.post("/notify", json=notif_payload)
    assert res_notif.status_code == 200
    assert res_notif.json()["status"] == "delivered"

    # Test Ticket
    ticket_payload = {
        "incident_id": "INC-20261008-001",
        "title": "[CRITICAL] Test Ticket Title",
        "severity": "CRITICAL",
        "description": "Test ticket description",
        "assignee": "NOC Tier-2"
    }
    res_ticket = client.post("/ticket", json=ticket_payload)
    assert res_ticket.status_code == 200
    assert res_ticket.json()["status"] == "created"
    assert "TICK-" in res_ticket.json()["ticket_id"]

def test_api_diagnostic_tools():
    res_ping = client.get("/tools/ping?node=LINK-A")
    assert res_ping.status_code == 200
    assert res_ping.json()["node"] == "LINK-A"

    res_kpi = client.get("/tools/kpi?node=CMG-02&kpi=bgp_session_state")
    assert res_kpi.status_code == 200
    assert res_kpi.json()["kpi_name"] == "bgp_session_state"
