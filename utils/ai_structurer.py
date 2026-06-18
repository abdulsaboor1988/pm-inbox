"""
AI structuring — uses the Anthropic API to extract structured feature requests
from unstructured email or meeting note content.
"""
import requests
import json
import re


ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
MODEL         = "claude-sonnet-4-6"


SYSTEM_PROMPT = """You are a PM assistant that extracts actionable product or engineering feature requests from emails and meeting notes.

Given a piece of text, extract ALL distinct actionable items. For each item return a JSON object with:
- title: short, clear title (max 10 words)
- description: what the problem or need is (1-2 sentences)
- impact: business impact or value (1 sentence, or empty string if not mentioned)
- priority: "High", "Medium", or "Low" based on language urgency cues (default "Medium")
- tool: production tool or system mentioned (e.g. PCS, DMP, or empty string)

Return ONLY a JSON array of objects. No markdown, no explanation, no preamble.
If there are no actionable items, return [].

Example output:
[{"title":"Add bulk export to CSV","description":"Users need to export order data in bulk for reporting","impact":"Saves 2h per week for ops team","priority":"Medium","tool":"DMP"}]"""


def structure_items(content: str, source_type: str = "email") -> list[dict]:
    """
    Send content to Claude and return a list of structured action items.
    source_type: "email" or "calendar"
    """
    if not content or not content.strip():
        return []

    user_msg = f"Extract actionable feature requests from this {source_type} content:\n\n{content[:4000]}"

    try:
        resp = requests.post(
            ANTHROPIC_API,
            headers={"Content-Type": "application/json"},
            json={
                "model":      MODEL,
                "max_tokens": 1000,
                "system":     SYSTEM_PROMPT,
                "messages":   [{"role": "user", "content": user_msg}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()

        # Strip markdown fences if present
        text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE).strip()

        items = json.loads(text)
        return items if isinstance(items, list) else []

    except json.JSONDecodeError:
        return []
    except Exception:
        return []


def build_capture_item(raw: dict, ai_item: dict, index: int = 0) -> dict:
    """
    Merge a raw email/calendar dict with an AI-extracted item into
    the standard inbox message format.
    """
    return {
        "id":          f"{raw['id']}_{index}",
        "source":      raw["source"],           # "gmail" | "calendar"
        "author":      raw["sender"],
        "time":        raw["date"],
        "title":       ai_item.get("title", raw.get("subject", "Untitled")),
        "tool":        ai_item.get("tool", ""),
        "description": ai_item.get("description", ""),
        "impact":      ai_item.get("impact", ""),
        "priority":    ai_item.get("priority", "Medium"),
        "status":      "pending",
        "ticket_key":  None,
        "quarter":     None,
        "start_date":  None,
        "end_date":    None,
        "objective":   None,
        # Extra capture metadata
        "source_subject": raw.get("subject", ""),
        "source_snippet": raw.get("snippet", ""),
        "meet_link":      raw.get("meet_link", ""),
        "attendees":      raw.get("attendees", []),
    }
