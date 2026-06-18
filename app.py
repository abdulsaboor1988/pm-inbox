import streamlit as st
import requests
import re
from datetime import datetime, date
from base64 import b64encode

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Production Tech · PM Inbox",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ──────────────────────────────────────────────────────────────────
JIRA_DOMAIN       = "hellofresh.atlassian.net"
JIRA_PROJECT      = "IX"
JIRA_ISSUETYPE_ID = "10001"
SLACK_CHANNEL_ID  = "C0BBA2LPDMH"
SLACK_BOT_ID      = "B0BBD679N0M"
HF_GREEN_DARK     = "#155724"
HF_GREEN          = "#1e7e34"

QUARTERS = ["—", "Q1", "Q2", "Q3", "Q4"]

STRATEGIC_OBJECTIVES = [
    "—",
    "Reduce operational waste & error rates",
    "Improve production speed & throughput",
    "Enhance data quality & traceability",
    "Automate manual processes",
    "Improve supplier & vendor management",
    "Scale production tech infrastructure",
    "Improve team tooling & developer experience",
    "Customer experience & fulfilment quality",
]

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

[data-testid="stSidebar"] {{ background: {HF_GREEN_DARK} !important; padding: 0 !important; }}
[data-testid="stSidebar"] > div:first-child {{ padding: 0; }}
[data-testid="stSidebarNav"] {{ display: none; }}

.hf-logo-bar {{ display:flex; align-items:center; gap:10px; padding:18px 20px 16px; border-bottom:1px solid rgba(255,255,255,0.12); margin-bottom:8px; }}
.hf-logo {{ background:white; border-radius:6px; width:32px; height:32px; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:800; color:{HF_GREEN_DARK}; flex-shrink:0; }}
.hf-app-name {{ font-size:13px; font-weight:600; color:white; line-height:1.2; }}
.hf-app-sub {{ font-size:11px; color:rgba(255,255,255,0.55); }}

.hf-user-bar {{ position:absolute; bottom:0; left:0; right:0; display:flex; align-items:center; gap:10px; padding:14px 20px; border-top:1px solid rgba(255,255,255,0.12); background:{HF_GREEN_DARK}; }}
.user-avatar {{ width:32px; height:32px; border-radius:50%; background:rgba(255,255,255,0.2); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; color:white; flex-shrink:0; }}
.user-name {{ font-size:13px; color:white; font-weight:500; }}
.user-role {{ font-size:11px; color:rgba(255,255,255,0.5); }}
.sso-badge {{ margin-left:auto; font-size:10px; background:rgba(255,255,255,0.12); color:rgba(255,255,255,0.6); padding:2px 7px; border-radius:99px; }}

.page-title {{ font-size:22px; font-weight:600; color:#1a1a1a; margin:0; }}
.page-sub {{ font-size:13px; color:#888; margin-top:2px; }}

.stat-row {{ display:flex; gap:12px; margin-bottom:1.5rem; }}
.stat-card {{ flex:1; background:white; border:1px solid #e8e8e6; border-radius:10px; padding:14px 18px; }}
.stat-label {{ font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px; }}
.stat-value {{ font-size:26px; font-weight:600; color:#1a1a1a; }}
.stat-value.green {{ color:{HF_GREEN}; }}
.stat-value.amber {{ color:#d97706; }}

.req-card {{ background:white; border:1px solid #e8e8e6; border-radius:10px; padding:1rem 1.25rem; margin-bottom:10px; }}
.req-card.pending  {{ border-left:4px solid #f59e0b; }}
.req-card.approved {{ border-left:4px solid {HF_GREEN}; }}
.req-card.dismissed {{ border-left:4px solid #d1d5db; opacity:0.65; }}
.req-title {{ font-size:15px; font-weight:600; color:#111; margin-bottom:2px; }}
.req-meta  {{ font-size:12px; color:#888; margin-bottom:10px; }}

.field-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px 24px; margin-bottom:10px; }}
.field-block {{ display:flex; flex-direction:column; gap:2px; }}
.field-block.full {{ grid-column:1/-1; }}
.fl {{ font-size:11px; color:#aaa; text-transform:uppercase; letter-spacing:0.05em; }}
.fv {{ font-size:13px; color:#222; line-height:1.45; }}

.meta-tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; padding-top:8px; border-top:1px solid #f3f4f6; }}
.meta-tag {{ display:inline-flex; align-items:center; gap:4px; font-size:11px; background:#f8f9fa; border:1px solid #e8e8e6; border-radius:6px; padding:3px 8px; color:#444; }}
.meta-tag b {{ color:#111; }}

.badge {{ display:inline-block; font-size:11px; padding:2px 9px; border-radius:99px; font-weight:600; margin-right:4px; }}
.b-pending   {{ background:#FEF3E2; color:#92400e; }}
.b-approved  {{ background:#d1fae5; color:#065f46; }}
.b-dismissed {{ background:#f3f4f6; color:#6b7280; }}
.b-high   {{ background:#fee2e2; color:#991b1b; }}
.b-medium {{ background:#fef3c7; color:#92400e; }}
.b-low    {{ background:#d1fae5; color:#065f46; }}

.ticket-link {{ display:inline-flex; align-items:center; gap:4px; font-size:12px; color:#2563eb; text-decoration:none; background:#eff6ff; padding:3px 10px; border-radius:99px; font-weight:500; }}

.approve-panel {{ background:#f8fdf9; border:1px solid #d1fae5; border-radius:10px; padding:1rem 1.25rem; margin-top:6px; margin-bottom:12px; }}
.approve-panel-title {{ font-size:13px; font-weight:600; color:#065f46; margin-bottom:12px; }}

.config-row {{ display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #f3f4f6; }}
.config-row:last-child {{ border-bottom:none; }}
.config-key {{ font-size:13px; color:#555; }}
.config-val {{ font-size:13px; color:#111; font-weight:500; font-family:monospace; }}

#MainMenu {{ visibility:hidden; }} footer {{ visibility:hidden; }}
[data-testid="stToolbar"] {{ display:none; }}
[data-testid="collapsedControl"] {{ display:none !important; }}
.main .block-container {{ padding:2rem 2.5rem 2rem; max-width:960px; }}
.stButton > button {{ border-radius:6px !important; font-size:13px !important; font-weight:500 !important; padding:5px 14px !important; }}
.stButton > button[kind="primary"] {{ background:{HF_GREEN} !important; border-color:{HF_GREEN} !important; color:white !important; }}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
for k, v in [("messages", []), ("page", "requests"), ("view", "pm"),
              ("user_cache", {}), ("approving_id", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

def secret(key, fallback=""):
    try: return st.secrets[key]
    except: return fallback

for k, v in [("jira_email", secret("jira_email", "abdul.saboor@hellofresh.com")),
              ("jira_token", secret("jira_token", "")),
              ("slack_token", secret("slack_token", ""))]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ────────────────────────────────────────────────────────────────────
def jira_auth(email, token):
    return "Basic " + b64encode(f"{email}:{token}".encode()).decode()

def initials(name):
    parts = (name or "?").split()
    return "".join(p[0] for p in parts[:2]).upper()

def resolve_slack_user(user_id: str, token: str) -> str:
    """Resolve a Slack user ID to a display name, with caching."""
    if not user_id or not token:
        return user_id
    cache = st.session_state.user_cache
    if user_id in cache:
        return cache[user_id]
    try:
        resp = requests.get(
            "https://slack.com/api/users.info",
            headers={"Authorization": f"Bearer {token}"},
            params={"user": user_id},
            timeout=5,
        )
        data = resp.json()
        if data.get("ok"):
            profile = data["user"].get("profile", {})
            name = profile.get("real_name") or profile.get("display_name") or user_id
            cache[user_id] = name
            return name
    except:
        pass
    return user_id

def parse_slack_messages(raw, slack_token):
    out = []
    for msg in raw:
        text = msg.get("text", "")
        ts   = msg.get("ts", "")
        if msg.get("bot_id") != SLACK_BOT_ID: continue
        if "Request Title" not in text: continue

        def extract(field):
            m = re.search(rf"\*{re.escape(field)}\*\s*\n(.+?)(?=\n\*|\Z)", text, re.DOTALL)
            return m.group(1).strip() if m else ""

        raw_requested_by = extract("Requested By")

        # Try to get display name from mention format <@U123|Name> first
        mention_with_name = re.search(r"<@([A-Z0-9]+)\|([^>]+)>", raw_requested_by)
        mention_id_only   = re.search(r"<@([A-Z0-9]+)>", raw_requested_by)

        if mention_with_name:
            author = mention_with_name.group(2)
        elif mention_id_only:
            # Resolve ID via Slack API
            author = resolve_slack_user(mention_id_only.group(1), slack_token)
        else:
            author = raw_requested_by or "Unknown"

        ts_float = float(ts) if ts else 0
        dt = datetime.fromtimestamp(ts_float).strftime("%-d %b, %H:%M") if ts_float else ""

        out.append({
            "id": ts, "author": author, "time": dt,
            "title":       extract("Request Title"),
            "tool":        extract("Select the Production Tool"),
            "description": extract("Description/User Problem"),
            "impact":      extract("Business Impact/Expected Value"),
            "priority":    extract("Priority"),
            "status": "pending", "ticket_key": None,
            # New enrichment fields
            "quarter": None, "start_date": None, "end_date": None,
            "objective": None,
        })
    return out

def fetch_slack(token):
    resp = requests.get(
        "https://slack.com/api/conversations.history",
        headers={"Authorization": f"Bearer {token}"},
        params={"channel": SLACK_CHANNEL_ID, "limit": 50},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise ValueError(data.get("error", "unknown"))
    return data.get("messages", [])

def fetch_jira_dates(ticket_key, email, token):
    """Fetch start & due date from Jira if set."""
    try:
        resp = requests.get(
            f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_key}?fields=duedate,customfield_10015,customfield_10014",
            headers={"Authorization": jira_auth(email, token)},
            timeout=8,
        )
        fields = resp.json().get("fields", {})
        start = fields.get("customfield_10015") or fields.get("customfield_10014")
        due   = fields.get("duedate")
        return start, due
    except:
        return None, None

def create_jira(msg, email, token):
    desc = "\n\n".join(filter(None, [
        f"Production Tool: {msg['tool']}"   if msg.get("tool")        else "",
        f"Problem: {msg['description']}"    if msg.get("description") else "",
        f"Business Impact: {msg['impact']}" if msg.get("impact")      else "",
        f"Priority: {msg['priority']}"      if msg.get("priority")    else "",
        f"Quarter: {msg.get('quarter','')}" if msg.get("quarter")     else "",
        f"Strategic Objective: {msg.get('objective','')}" if msg.get("objective") else "",
        f"Requested by: {msg['author']}",
        f"Source: Slack #product-requests-production ({msg['time']})",
    ]))

    fields = {
        "project":   {"key": JIRA_PROJECT},
        "summary":   msg["title"] or "Untitled request",
        "description": {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc}]}],
        },
        "issuetype": {"id": JIRA_ISSUETYPE_ID},
    }
    # Set due date if provided
    if msg.get("end_date"):
        fields["duedate"] = str(msg["end_date"])

    resp = requests.post(
        f"https://{JIRA_DOMAIN}/rest/api/3/issue",
        headers={"Content-Type": "application/json", "Authorization": jira_auth(email, token)},
        json={"fields": fields},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["key"]

def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'

def status_badge(s):
    return badge({"pending":"Pending","approved":"✓ Approved","dismissed":"Dismissed"}.get(s,s),
                 {"pending":"b-pending","approved":"b-approved","dismissed":"b-dismissed"}.get(s,"b-pending"))

def priority_badge(p):
    if not p: return ""
    cls = "b-high" if "high" in p.lower() else "b-low" if "low" in p.lower() else "b-medium"
    return badge(p, cls)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="hf-logo-bar">
        <div class="hf-logo">HF</div>
        <div><div class="hf-app-name">Production Tech</div><div class="hf-app-sub">PM Inbox</div></div>
    </div>""", unsafe_allow_html=True)

    for page_id, icon, label in [("requests","📥","Requests"), ("configuration","⚙️","Configuration")]:
        if st.button(f"{icon}  {label}", key=f"nav_{page_id}", use_container_width=True,
                     type="primary" if st.session_state.page == page_id else "secondary"):
            st.session_state.page = page_id
            st.session_state.approving_id = None
            st.rerun()

    st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
    user_name = "Abdul Saboor"
    st.markdown(f"""
    <div class="hf-user-bar">
        <div class="user-avatar">{initials(user_name)}</div>
        <div><div class="user-name">{user_name}</div><div class="user-role">PM · Production Tech</div></div>
        <div class="sso-badge">SSO</div>
    </div>""", unsafe_allow_html=True)


# ── Page: Requests ─────────────────────────────────────────────────────────────
def page_requests():
    total    = len(st.session_state.messages)
    pending  = sum(1 for m in st.session_state.messages if m["status"] == "pending")
    approved = sum(1 for m in st.session_state.messages if m["status"] == "approved")
    dismissed = total - pending - approved

    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.markdown('<p class="page-title">Feature request inbox</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">Slack #product-requests-production → Jira IX · Production Tech Developments</p>', unsafe_allow_html=True)
    with col_btn:
        if st.button("🔄 Refresh", type="primary", use_container_width=True):
            token = st.session_state.slack_token
            if not token:
                st.error("Add Slack token in Configuration first.")
            else:
                with st.spinner("Fetching from Slack…"):
                    try:
                        raw    = fetch_slack(token)
                        parsed = parse_slack_messages(raw, token)
                        existing = {m["id"] for m in st.session_state.messages}
                        new = [m for m in parsed if m["id"] not in existing]
                        st.session_state.messages = new + st.session_state.messages
                        st.success(f"{len(new)} new request(s) loaded." if new else "Already up to date.")
                    except Exception as e:
                        st.error(f"Slack error: {e}")

    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card"><div class="stat-label">Total</div><div class="stat-value">{total}</div></div>
        <div class="stat-card"><div class="stat-label">Pending review</div><div class="stat-value amber">{pending}</div></div>
        <div class="stat-card"><div class="stat-label">Approved</div><div class="stat-value green">{approved}</div></div>
        <div class="stat-card"><div class="stat-label">Dismissed</div><div class="stat-value">{dismissed}</div></div>
    </div>""", unsafe_allow_html=True)

    tab_all, tab_pending, tab_approved, tab_dismissed = st.tabs([
        f"All ({total})", f"Pending ({pending})", f"Approved ({approved})", f"Dismissed ({dismissed})"
    ])

    def render(msgs, tab_key, actions=True):
        if not msgs:
            st.markdown("<div style='padding:2rem;text-align:center;color:#aaa'>No requests here.</div>", unsafe_allow_html=True)
            return

        for i, msg in enumerate(msgs):
            s  = msg["status"]
            tk = msg.get("ticket_key")
            ticket_html = f'<a class="ticket-link" href="https://{JIRA_DOMAIN}/browse/{tk}" target="_blank">🎫 {tk}</a>' if tk else ""

            # Build enrichment meta tags for approved cards
            meta_tags = ""
            if s == "approved":
                tags = []
                if msg.get("quarter"):    tags.append(f'<span class="meta-tag">📅 <b>{msg["quarter"]}</b></span>')
                if msg.get("start_date"): tags.append(f'<span class="meta-tag">▶ Start <b>{msg["start_date"]}</b></span>')
                if msg.get("end_date"):   tags.append(f'<span class="meta-tag">⏹ End <b>{msg["end_date"]}</b></span>')
                if msg.get("objective"):  tags.append(f'<span class="meta-tag">🎯 <b>{msg["objective"]}</b></span>')
                if tags:
                    meta_tags = f'<div class="meta-tags">{"".join(tags)}</div>'

            st.markdown(f"""
            <div class="req-card {s}">
                <div class="req-title">{msg['title'] or 'Untitled'}</div>
                <div class="req-meta">{msg['author']} &nbsp;·&nbsp; {msg['time']}</div>
                <div class="field-grid">
                    {'<div class="field-block"><div class="fl">Tool</div><div class="fv">' + msg['tool'] + '</div></div>' if msg.get('tool') else ''}
                    {'<div class="field-block"><div class="fl">Problem</div><div class="fv">' + msg['description'] + '</div></div>' if msg.get('description') else ''}
                    {'<div class="field-block full"><div class="fl">Business impact</div><div class="fv">' + msg['impact'] + '</div></div>' if msg.get('impact') else ''}
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
                    {status_badge(s)}{priority_badge(msg.get('priority',''))}{ticket_html}
                </div>
                {meta_tags}
            </div>""", unsafe_allow_html=True)

            # ── Approve panel (shown when this card is being approved) ──
            card_uid = f"{tab_key}_{i}"
            is_approving = st.session_state.approving_id == f"{msg['id']}_{tab_key}"

            if actions and s == "pending":
                if not is_approving:
                    a_col, d_col, _ = st.columns([1, 1, 5])
                    with a_col:
                        if st.button("✅ Approve", key=f"app_{card_uid}", type="primary"):
                            st.session_state.approving_id = f"{msg['id']}_{tab_key}"
                            st.rerun()
                    with d_col:
                        if st.button("✗ Dismiss", key=f"dis_{card_uid}"):
                            msg["status"] = "dismissed"
                            st.rerun()
                else:
                    # ── Approval enrichment panel ──
                    st.markdown('<div class="approve-panel"><div class="approve-panel-title">📋 Set ticket details before creating in Jira</div>', unsafe_allow_html=True)

                    ec1, ec2 = st.columns(2)
                    with ec1:
                        quarter = st.selectbox("Quarter", QUARTERS, key=f"q_{card_uid}")
                    with ec2:
                        objective = st.selectbox("Strategic objective", STRATEGIC_OBJECTIVES, key=f"obj_{card_uid}")

                    dc1, dc2 = st.columns(2)
                    with dc1:
                        start_date = st.date_input("Start date (optional)", value=None, key=f"sd_{card_uid}")
                    with dc2:
                        end_date = st.date_input("End date / due date (optional)", value=None, key=f"ed_{card_uid}")

                    st.markdown("</div>", unsafe_allow_html=True)

                    conf_col, cancel_col, _ = st.columns([1.2, 1, 4])
                    with conf_col:
                        if st.button("🎫 Create Jira ticket", key=f"confirm_{card_uid}", type="primary"):
                            jt = st.session_state.jira_token
                            je = st.session_state.jira_email
                            if not jt:
                                st.error("Add Jira token in Configuration first.")
                            else:
                                # Save enrichment back to msg
                                msg["quarter"]    = quarter if quarter != "—" else None
                                msg["objective"]  = objective if objective != "—" else None
                                msg["start_date"] = str(start_date) if start_date else None
                                msg["end_date"]   = str(end_date) if end_date else None

                                with st.spinner("Creating Jira ticket…"):
                                    try:
                                        key = create_jira(msg, je, jt)
                                        msg["status"]     = "approved"
                                        msg["ticket_key"] = key
                                        st.session_state.approving_id = None
                                        st.success(f"{key} created ✓")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Jira error: {e}")
                    with cancel_col:
                        if st.button("Cancel", key=f"cancel_{card_uid}"):
                            st.session_state.approving_id = None
                            st.rerun()

    with tab_all:       render(st.session_state.messages, "all")
    with tab_pending:   render([m for m in st.session_state.messages if m["status"] == "pending"], "pend")
    with tab_approved:  render([m for m in st.session_state.messages if m["status"] == "approved"], "appr", actions=False)
    with tab_dismissed: render([m for m in st.session_state.messages if m["status"] == "dismissed"], "dism", actions=False)


# ── Page: Configuration ────────────────────────────────────────────────────────
def page_configuration():
    st.markdown('<p class="page-title">Configuration</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Manage credentials and integration settings</p>', unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:1.25rem'></div>", unsafe_allow_html=True)

    with st.expander("🎫  Jira", expanded=True):
        st.markdown(f"""
        <div class="config-row"><span class="config-key">Instance</span><span class="config-val">{JIRA_DOMAIN}</span></div>
        <div class="config-row"><span class="config-key">Project</span><span class="config-val">{JIRA_PROJECT} · Production Tech Developments</span></div>
        <div class="config-row"><span class="config-key">Issue type</span><span class="config-val">Story (ID {JIRA_ISSUETYPE_ID})</span></div>
        <div class="config-row"><span class="config-key">Board</span><span class="config-val">1239</span></div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        new_email = st.text_input("Atlassian email", value=st.session_state.jira_email, key="cfg_jira_email")
        new_token = st.text_input("Atlassian API token", value=st.session_state.jira_token, type="password", placeholder="ATATT3x…", key="cfg_jira_token")
        if st.button("Save Jira credentials", key="save_jira"):
            st.session_state.jira_email = new_email
            st.session_state.jira_token = new_token
            st.success("Jira credentials saved.")

    with st.expander("💬  Slack", expanded=True):
        st.markdown(f"""
        <div class="config-row"><span class="config-key">Channel</span><span class="config-val">#product-requests-production</span></div>
        <div class="config-row"><span class="config-key">Channel ID</span><span class="config-val">{SLACK_CHANNEL_ID}</span></div>
        <div class="config-row"><span class="config-key">Bot</span><span class="config-val">Production Tech - Feature Requests</span></div>
        <div class="config-row"><span class="config-key">Bot ID</span><span class="config-val">{SLACK_BOT_ID}</span></div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        new_slack = st.text_input("Slack Bot token", value=st.session_state.slack_token, type="password", placeholder="xoxb-…", key="cfg_slack_token")
        if st.button("Save Slack token", key="save_slack"):
            st.session_state.slack_token = new_slack
            st.success("Slack token saved.")

    with st.expander("🎯  Strategic objectives", expanded=False):
        st.caption("These appear as options when approving a request. Edit the STRATEGIC_OBJECTIVES list in app.py to customise.")
        for obj in STRATEGIC_OBJECTIVES[1:]:
            st.markdown(f"- {obj}")

    with st.expander("👥  Access & view mode", expanded=False):
        st.markdown("""
        <div class="config-row"><span class="config-key">SSO integration</span><span class="config-val">Planned — HF SSO</span></div>
        <div class="config-row"><span class="config-key">Current user</span><span class="config-val">Abdul Saboor</span></div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        view = st.radio("View mode", ["PM (full access — approve/dismiss)", "Stakeholder (read-only)"],
                        index=0 if st.session_state.view == "pm" else 1, key="cfg_view")
        st.session_state.view = "readonly" if "Stakeholder" in view else "pm"
        st.caption("When HF SSO is integrated, view mode will be set automatically based on the logged-in user's role.")


# ── Router ─────────────────────────────────────────────────────────────────────
if st.session_state.page == "requests":
    page_requests()
elif st.session_state.page == "configuration":
    page_configuration()
