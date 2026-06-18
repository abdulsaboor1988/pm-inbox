"""
Google Calendar API helpers — fetch recent meetings and extract notes/descriptions.
"""
import requests
from datetime import datetime, timedelta, timezone


CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def list_calendars(token: str) -> list[dict]:
    resp = requests.get(
        f"{CALENDAR_BASE}/users/me/calendarList",
        headers=_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def fetch_meetings(token: str, days_back: int = 14, max_results: int = 20) -> list[dict]:
    """
    Fetch recent calendar events that look like meetings with notes.
    Returns events that have a description, notes, or attendees.
    """
    now       = datetime.now(timezone.utc)
    time_min  = (now - timedelta(days=days_back)).isoformat()
    time_max  = now.isoformat()

    resp = requests.get(
        f"{CALENDAR_BASE}/calendars/primary/events",
        headers=_headers(token),
        params={
            "timeMin":      time_min,
            "timeMax":      time_max,
            "maxResults":   max_results,
            "orderBy":      "startTime",
            "singleEvents": "true",
        },
        timeout=10,
    )
    resp.raise_for_status()
    events = resp.json().get("items", [])

    meetings = []
    for ev in events:
        # Skip events with no useful content
        description = ev.get("description", "").strip()
        attendees   = ev.get("attendees", [])
        summary     = ev.get("summary", "(no title)")

        if not description and len(attendees) < 2:
            continue  # Skip solo events / blocks with no notes

        start_raw = ev.get("start", {})
        start_dt  = start_raw.get("dateTime") or start_raw.get("date", "")
        try:
            if "T" in start_dt:
                dt_obj = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                date_str = dt_obj.strftime("%-d %b, %H:%M")
            else:
                date_str = start_dt
        except Exception:
            date_str = start_dt

        organizer = ev.get("organizer", {}).get("displayName") or ev.get("organizer", {}).get("email", "")
        attendee_names = [
            a.get("displayName") or a.get("email", "")
            for a in attendees
            if not a.get("self")
        ]

        meetings.append({
            "id":          f"gcal_{ev.get('id', '')}",
            "event_id":    ev.get("id", ""),
            "source":      "calendar",
            "subject":     summary,
            "sender":      organizer,
            "date":        date_str,
            "body":        description,
            "snippet":     description[:200] if description else f"Meeting with {', '.join(attendee_names[:3])}",
            "attendees":   attendee_names,
            "meet_link":   ev.get("hangoutLink", ""),
        })

    return meetings
