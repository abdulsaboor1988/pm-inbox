"""
Gmail API helpers — fetch emails and return structured message dicts.
"""
import requests
import base64
import re
from datetime import datetime


GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def list_messages(token: str, query: str = "", max_results: int = 20) -> list[dict]:
    """
    List Gmail messages matching a query.
    Default query targets emails likely to contain product/feature requests.
    """
    if not query:
        query = "subject:(feature OR request OR feedback OR improvement OR bug) -from:me newer_than:30d"

    resp = requests.get(
        f"{GMAIL_BASE}/messages",
        headers=_headers(token),
        params={"q": query, "maxResults": max_results},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("messages", [])


def get_message(token: str, msg_id: str) -> dict:
    """Fetch a single Gmail message and return a clean dict."""
    resp = requests.get(
        f"{GMAIL_BASE}/messages/{msg_id}",
        headers=_headers(token),
        params={"format": "full"},
        timeout=10,
    )
    resp.raise_for_status()
    raw = resp.json()

    headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}
    subject  = headers.get("subject", "(no subject)")
    sender   = _parse_sender(headers.get("from", ""))
    date_str = headers.get("date", "")
    body     = _extract_body(raw.get("payload", {}))
    ts       = int(raw.get("internalDate", 0)) // 1000
    dt       = datetime.fromtimestamp(ts).strftime("%-d %b, %H:%M") if ts else ""

    return {
        "id":      f"gmail_{msg_id}",
        "msg_id":  msg_id,
        "source":  "gmail",
        "subject": subject,
        "sender":  sender,
        "date":    dt,
        "body":    body[:3000],  # cap for AI processing
        "snippet": raw.get("snippet", ""),
        "thread_id": raw.get("threadId", ""),
    }


def _parse_sender(from_header: str) -> str:
    """Extract display name from 'Name <email@example.com>' format."""
    m = re.match(r'^"?([^"<]+)"?\s*<', from_header)
    if m:
        return m.group(1).strip()
    m = re.match(r"([^<@\s]+@[^\s>]+)", from_header)
    if m:
        return m.group(1)
    return from_header or "Unknown"


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from Gmail payload."""
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    if mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            # Strip tags
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text

    # Multipart — recurse into parts
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result

    return ""


def fetch_emails(token: str, query: str = "", max_results: int = 20) -> list[dict]:
    """Fetch and return full email dicts for messages matching query."""
    ids = list_messages(token, query, max_results)
    emails = []
    for item in ids:
        try:
            emails.append(get_message(token, item["id"]))
        except Exception:
            continue
    return emails
