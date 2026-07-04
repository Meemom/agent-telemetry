from __future__ import annotations


def send_email(to: str, subject: str, body: str) -> dict[str, str]:
    """Record an attempted email action without sending anything."""

    return {
        "attempted_tool": "send_email",
        "to": to,
        "subject": subject,
        "body": body,
        "sent": "false",
    }
