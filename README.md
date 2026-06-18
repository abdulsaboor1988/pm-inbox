# PM Inbox — Production Tech Feature Requests

Streamlit app that pulls feature requests from Slack `#product-requests-production` and lets PMs approve them to auto-create Jira Stories in project **IX** (Production Tech Developments, `hellofresh.atlassian.net`).

## Views

| View | Who | Can do |
|------|-----|--------|
| PM (full access) | You | Fetch Slack, approve → create ticket, dismiss |
| Stakeholder (read-only) | Requesters / leadership | See request status + live Jira ticket status |

---

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 and enter credentials in the sidebar.

---

## Credentials needed

### Jira API token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create a token, copy it
3. Paste into the sidebar (or `secrets.toml` for deployment)

### Slack Bot token
The app needs a Slack bot token with these scopes on `#product-requests-production`:
- `channels:history` — read messages
- `channels:read` — resolve channel info

To get one:
1. Go to https://api.slack.com/apps → Create New App → From Scratch
2. Add OAuth scopes: `channels:history`, `channels:read`
3. Install to workspace → copy the **Bot User OAuth Token** (`xoxb-…`)
4. Invite the bot to `#product-requests-production`: `/invite @your-bot-name`

---

## Deploy to Streamlit Cloud (recommended for stakeholder access)

1. Push this folder to a GitHub repo (make sure `.streamlit/secrets.toml` is in `.gitignore`)
2. Go to https://share.streamlit.io → New app → point to your repo + `app.py`
3. Under **Secrets**, paste:
```toml
jira_email = "abdul.saboor@hellofresh.com"
jira_token = "your-atlassian-api-token"
slack_token = "xoxb-your-slack-bot-token"
```
4. Share the public URL with stakeholders — they select **Stakeholder (read-only)** view

---

## Share read-only link cleanly

To default stakeholders to read-only view, append `?view=readonly` to the URL and add this to the top of `app.py`:

```python
params = st.query_params
if params.get("view") == "readonly":
    st.session_state.view = "readonly"
```

---

## Project structure

```
pm-inbox/
├── app.py                  # Main Streamlit app
├── requirements.txt
├── .streamlit/
│   └── secrets.toml        # Local credentials (never commit)
└── README.md
```
