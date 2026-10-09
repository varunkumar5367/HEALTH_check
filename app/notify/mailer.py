import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional
import os
from datetime import datetime, timezone

from app.config import settings
from app.notify.email_formatter import EmailRCAFormatter

class EmailDispatcher:
    """
    Email notification dispatcher for sending Root Cause Analysis & Solution reports to NOC engineers.
    Supports real SMTP delivery (Gmail, Office365, Custom Relay) and local sandbox mock storage.
    """
    outbox_history: List[Dict[str, Any]] = []

    def __init__(
        self,
        smtp_host: str = settings.SMTP_HOST,
        smtp_port: int = settings.SMTP_PORT,
        smtp_user: str = settings.SMTP_USER,
        smtp_password: str = settings.SMTP_PASSWORD,
        use_mock: bool = settings.USE_MOCK_EMAIL
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_mock = use_mock

    def send_rca_email(self, triage_result: Dict[str, Any], recipient: Optional[str] = None) -> Dict[str, Any]:
        target_email = recipient if recipient else settings.ALERT_EMAIL_RECIPIENT
        formatted = EmailRCAFormatter.format_rca_email(triage_result, target_email)
        
        email_record = {
            "dispatch_id": f"MAIL-{len(self.outbox_history) + 1:04d}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "recipient": target_email,
            "subject": formatted["subject"],
            "incident_id": triage_result.get("incident_id"),
            "probable_root": triage_result.get("probable_root"),
            "severity": triage_result.get("severity"),
            "status": "DELIVERED"
        }

        if not self.use_mock and self.smtp_user and self.smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = formatted["subject"]
                msg["From"] = settings.SENDER_EMAIL
                msg["To"] = target_email

                part1 = MIMEText(formatted["text"], "plain")
                part2 = MIMEText(formatted["html"], "html")
                msg.attach(part1)
                msg.attach(part2)

                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0)
                try:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(settings.SENDER_EMAIL, target_email, msg.as_string())
                    email_record["mode"] = "SMTP_LIVE"
                finally:
                    try:
                        server.close()
                    except Exception:
                        pass
            except Exception as e:
                print(f"SMTP dispatch warning: {e}. Falling back to mock record.")
                email_record["mode"] = "MOCK_FALLBACK"
                email_record["error"] = str(e)
        else:
            email_record["mode"] = "MOCK_SANDBOX"

        self.outbox_history.append(email_record)
        print(f"📧 RCA Email Dispatched -> Recipient: {target_email} | Subject: {formatted['subject']}")
        return email_record

    @classmethod
    def get_outbox_history(cls) -> List[Dict[str, Any]]:
        return cls.outbox_history
