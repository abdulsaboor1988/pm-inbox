import streamlit as st
import requests
import json
from datetime import datetime
from base64 import b64encode

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PM Inbox · Production Tech",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ──────────────────────────────────────────────────────────────────
JIRA_DOMAIN   = "hellofresh.atlassian.net"
JIRA_PROJECT  = "IX"
JIRA_ISSUETYPE_ID = "10001"   # Story
SLACK_CHANNEL_ID  = "C0BBA2LPDMH"
SLACK_BOT_ID      = "B0BBD679N0M"  # Production Tech - Feature Requests bot

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar */
[data-testid="stSidebar"] { background: #f8f8f7; }

/* Cards */
.request-card {
    background: white;
    border: 1px solid #e8e8e6;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 12px;
}
.request-card.approved { border-left: 4px solid #1D9E75; }
.request-card.dismissed { border-left: 4px solid #d0d0ce; opacity: 0.6; }
.request-card.pending { border-left: 4px solid #F8A623; }

/* Badges */
.badge {
    display: inline-block;
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 99px;
    font-weight: 600;
    margin-right: 6px;
}
.badge-approved  { background: #E1F5EE; color: #0F6E56; }
.badge-dismissed { background: #f0f0ee; color: #888; }
.badge-pending   { background: #FEF3E2; color: #854F0B; }
.badge-high   { background: #FCEBEB; color: #A32D2D; }
.badge-medium { background: #FAEEDA; color: #854F0B; }
.badge-low    { background: #EAF3DE; color: #3B6D11; }

/* Field labels */
.field-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
.field-value { font-size: 14px; color: #1a1a1a; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "view" not in st.session_state:
    st.session_state.view = "pm"  # "pm" or "readonly"


# ── Helpers ────────────────────────────────────────────────────────────────────
def jira_auth_header(email: str, token: str) -> str:
    return "Basic " + b64encode(f"{email}:{token}".encode()).decode()


def parse_slack_messages(raw_messages: list) -> list:
    """Parse structured bot messages from the Slack channel."""
    requests_out = []
    for msg in raw_messages:
        text = msg.get("text", "")
        ts   = msg.get("ts", "")
        user = msg.get("user", "")
        bot  = msg.get("bot_id", "")

        # Only process structured bot messages
        if bot != SLACK_BOT_ID:
            continue
        if "Request Title" not in text:
            continue

        def extract(field):
            import re
            pattern = rf"\*{re.escape(field)}\*\s*\n(.+?)(?=\n\*|\Z)"
            m = re.search(pattern, text, re.DOTALL)
            return m.group(1).strip() if m else ""

        # Parse Requested By — strip Slack user mention formatting
        requested_by = extract("Requested By")
        import re
        requested_by = re.sub(r"<@[A-Z0-9]+\|([^>]+)>", r"\1", requested_by)

        ts_float = float(ts) if ts else 0
        dt = datetime.fromtimestamp(ts_float).strftime("%-d %b, %H:%M") if ts_float else ""

        requests_out.append({
            "id":          ts,
            "author":      requested_by or "Unknown",
            "time":        dt,
            "title":       extract("Request Title"),
            "tool":        extract("Select the Production Tool"),
            "description": extract("Description/User Problem"),
            "impact":      extract("Business Impact/Expected Value"),
            "priority":    extract("Priority"),
            "status":      "pending",
            "ticket_key":  None,
        })

    return requests_out


def fetch_slack_messages(slack_token: str) -> list:
    """Fetch messages from Slack channel via API."""
    url = "https://slack.com/api/conversations.history"
    headers = {"Authorization": f"Bearer {slack_token}"}
    params  = {"channel": SLACK_CHANNEL_ID, "limit": 50}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise ValueError(f"Slack error: {data.get('error', 'unknown')}")
    return data.get("messages", [])


def create_jira_ticket(msg: dict, jira_email: str, jira_token: str) -> str:
    """Create a Jira Story in project IX. Returns the ticket key."""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"
    headers = {
        "Content-Type": "application/json",
        "Authorization": jira_auth_header(jira_email, jira_token),
    }
    description_text = "\n\n".join(filter(None, [
        f"Production Tool: {msg['tool']}"        if msg.get("tool")        else "",
        f"Problem: {msg['description']}"         if msg.get("description") else "",
        f"Business Impact: {msg['impact']}"      if msg.get("impact")      else "",
        f"Priority: {msg['priority']}"           if msg.get("priority")    else "",
        f"Requested by: {msg['author']}",
        f"Source: Slack #product-requests-production ({msg['time']})",
    ]))
    body = {
        "fields": {
            "project":     {"key": JIRA_PROJECT},
            "summary":     msg["title"] or "Untitled request",
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description_text}]}],
            },
            "issuetype": {"id": JIRA_ISSUETYPE_ID},
        }
    }
    resp = requests.post(url, headers=headers, json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()["key"]


def get_jira_ticket_status(ticket_key: str, jira_email: str, jira_token: str) -> dict:
    """Fetch current status of a Jira ticket."""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_key}?fields=status,summary,assignee,updated"
    headers = {"Authorization": jira_auth_header(jira_email, jira_token)}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    d = resp.json()["fields"]
    return {
        "status":   d["status"]["name"],
        "assignee": (d.get("assignee") or {}).get("displayName", "Unassigned"),
        "updated":  d.get("updated", "")[:10],
    }


def priority_badge(priority: str) -> str:
    p = (priority or "").lower()
    cls = "badge-high" if "high" in p else "badge-low" if "low" in p else "badge-medium"
    return f'<span class="badge {cls}">{priority}</span>' if priority else ""


def status_badge(status: str) -> str:
    cls = {"approved": "badge-approved", "dismissed": "badge-dismissed"}.get(status, "badge-pending")
    label = {"approved": "✓ Approved", "dismissed": "Dismissed", "pending": "Pending"}.get(status, status)
    return f'<span class="badge {cls}">{label}</span>'


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    view_mode = st.radio("View", ["PM (full access)", "Stakeholder (read-only)"], index=0)
    st.session_state.view = "readonly" if "Stakeholder" in view_mode else "pm"

    st.divider()
    st.markdown("**Jira**")
    jira_email = st.text_input("Atlassian email", value="abdul.saboor@hellofresh.com")
    jira_token = st.text_input("Atlassian API token", type="password", placeholder="ATATT3x…")

    st.divider()
    st.markdown("**Slack**")
    slack_token = st.text_input("Slack Bot token", type="password", placeholder="xoxb-…",
                                help="Needs channels:history + channels:read scopes on #product-requests-production")

    st.divider()
    if st.button("🔄 Fetch from Slack", use_container_width=True):
        if not slack_token:
            st.error("Enter a Slack bot token first.")
        else:
            with st.spinner("Fetching…"):
                try:
                    raw = fetch_slack_messages(slack_token)
                    parsed = parse_slack_messages(raw)
                    existing_ids = {m["id"] for m in st.session_state.messages}
                    new_msgs = [m for m in parsed if m["id"] not in existing_ids]
                    st.session_state.messages = new_msgs + st.session_state.messages
                    st.success(f"{len(new_msgs)} new request(s) loaded." if new_msgs else "No new requests.")
                except Exception as e:
                    st.error(f"Slack error: {e}")

    total   = len(st.session_state.messages)
    pending = sum(1 for m in st.session_state.messages if m["status"] == "pending")
    approved= sum(1 for m in st.session_state.messages if m["status"] == "approved")
    st.markdown(f"**{total}** total · **{pending}** pending · **{approved}** approved")


# ── Main layout ────────────────────────────────────────────────────────────────
st.markdown("## 📥 Feature Request Inbox")
st.caption(f"Slack #product-requests-production  →  Jira {JIRA_PROJECT} · Production Tech Developments")

# Filter tabs
tab_all, tab_pending, tab_approved, tab_dismissed = st.tabs(["All", "Pending", "Approved", "Dismissed"])

def render_messages(msgs, allow_actions=True):
    if not msgs:
        st.info("No requests in this view.")
        return

    for i, msg in enumerate(msgs):
        status = msg["status"]
        card_class = f"request-card {status}"

        with st.container():
            # Header row
            col_meta, col_status = st.columns([3, 1])
            with col_meta:
                st.markdown(f"**{msg['title'] or 'Untitled'}**")
                st.caption(f"{msg['author']} · {msg['time']}")
            with col_status:
                st.markdown(
                    status_badge(status) + ("&nbsp;" + priority_badge(msg["priority"]) if msg.get("priority") else ""),
                    unsafe_allow_html=True
                )

            # Fields
            cols = st.columns(2)
            if msg.get("tool"):
                with cols[0]:
                    st.markdown('<div class="field-label">Tool</div>', unsafe_allow_html=True)
                    st.markdown(msg["tool"])
            if msg.get("description"):
                with cols[1]:
                    st.markdown('<div class="field-label">Problem</div>', unsafe_allow_html=True)
                    st.markdown(msg["description"])
            if msg.get("impact"):
                st.markdown('<div class="field-label">Business impact</div>', unsafe_allow_html=True)
                st.markdown(msg["impact"])

            # Ticket link / status
            if msg.get("ticket_key"):
                ticket_url = f"https://{JIRA_DOMAIN}/browse/{msg['ticket_key']}"
                st.markdown(f"🎫 [{msg['ticket_key']}]({ticket_url})", unsafe_allow_html=False)

                # Stakeholder view: show live Jira status
                if st.session_state.view == "readonly" and jira_token:
                    try:
                        jira_status = get_jira_ticket_status(msg["ticket_key"], jira_email, jira_token)
                        st.caption(f"Status: **{jira_status['status']}** · Assignee: {jira_status['assignee']} · Updated: {jira_status['updated']}")
                    except:
                        pass

            # Actions (PM only)
            if allow_actions and st.session_state.view == "pm" and status == "pending":
                a_col, d_col, _ = st.columns([1, 1, 4])
                with a_col:
                    if st.button("✅ Approve", key=f"approve_{i}_{msg['id']}"):
                        if not jira_token:
                            st.error("Enter Jira API token in sidebar first.")
                        else:
                            with st.spinner("Creating Jira ticket…"):
                                try:
                                    key = create_jira_ticket(msg, jira_email, jira_token)
                                    msg["status"] = "approved"
                                    msg["ticket_key"] = key
                                    st.success(f"Created {key} ✓")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Jira error: {e}")
                with d_col:
                    if st.button("✗ Dismiss", key=f"dismiss_{i}_{msg['id']}"):
                        msg["status"] = "dismissed"
                        st.rerun()

            st.divider()


with tab_all:
    render_messages(st.session_state.messages)

with tab_pending:
    render_messages([m for m in st.session_state.messages if m["status"] == "pending"])

with tab_approved:
    render_messages([m for m in st.session_state.messages if m["status"] == "approved"], allow_actions=False)

with tab_dismissed:
    render_messages([m for m in st.session_state.messages if m["status"] == "dismissed"], allow_actions=False)
