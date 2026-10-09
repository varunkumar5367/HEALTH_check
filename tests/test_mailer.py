import pytest
from app.notify.email_formatter import EmailRCAFormatter
from app.notify.mailer import EmailDispatcher

def test_email_rca_formatter():
    triage_sample = {
        "incident_id": "INC-TEST-001",
        "probable_root": "LINK-A (Physical Fiber Link Down)",
        "probable_root_node": "LINK-A",
        "probable_root_code": "LINK_DOWN",
        "severity": "CRITICAL",
        "confidence_score": 0.95,
        "grouping_rationale": "Test grouping rationale.",
        "symptoms": ["CMG-02 - BGP Peer Session Down"],
        "cited_next_checks": [{"citation": "RB-01_Transport_Link_Down.md#3. Next Checks", "content": "Check optical power levels."}],
        "draft_ticket": {"ticket_id": "TICK-TEST-001", "title": "[CRITICAL] Test Ticket", "assignee": "NOC Tier-2"}
    }

    formatted = EmailRCAFormatter.format_rca_email(triage_sample, recipient="engineer@telco.com")
    assert "INC-TEST-001" in formatted["subject"]
    assert "LINK-A" in formatted["subject"]
    assert "RB-01_Transport_Link_Down.md" in formatted["html"]
    assert "Check optical power levels" in formatted["html"]

def test_email_dispatcher():
    dispatcher = EmailDispatcher()
    triage_sample = {
        "incident_id": "INC-TEST-002",
        "probable_root": "CMG-01 (CPU Utilization Exceeds Threshold)",
        "probable_root_node": "CMG-01",
        "probable_root_code": "CPU_HIGH",
        "severity": "CRITICAL",
        "confidence_score": 0.90,
        "symptoms": [],
        "cited_next_checks": []
    }

    record = dispatcher.send_rca_email(triage_sample, recipient="noc-lead@telco.com")
    assert record["recipient"] == "noc-lead@telco.com"
    assert record["mode"] == "SMTP_LIVE"
    assert len(EmailDispatcher.get_outbox_history()) > 0
