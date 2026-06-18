"""
Google OAuth 2.0 helpers for Gmail and Calendar access.
Uses the authorization code flow with PKCE, storing tokens in Streamlit session state.
"""
import streamlit as st
import requests
import urllib.parse
import hashlib
import base64
import os
import json
from datetime import datetime, timedelta

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
    "profile",
]


def _secret(key, fallback=""):
    try:
        return st.secrets[key]
    except Exception:
        return fallback


def get_client_id() -> str:
    return st.session_state.get("google_client_id") or _secret("google_client_id", "")


def get_client_secret() -> str:
    return st.session_state.get("google_client_secret") or _secret("google_client_secret", "")


def get_redirect_uri() -> str:
    """Build redirect URI from the current Streamlit app URL."""
    uri = st.session_state.get("google_redirect_uri") or _secret("google_redirect_uri", "")
    if uri:
        return uri
    # Fallback for local dev
    return "http://localhost:8501"


def is_configured() -> bool:
    return bool(get_client_id() and get_client_secret())


def is_authenticated() -> bool:
    return bool(
        st.session_state.get("google_access_token")
        and st.session_state.get("google_token_expiry")
        and datetime.utcnow() < st.session_state["google_token_expiry"]
    )


def get_access_token() -> str | None:
    """Return a valid access token, refreshing if needed."""
    if not st.session_state.get("google_access_token"):
        return None
    expiry = st.session_state.get("google_token_expiry")
    if expiry and datetime.utcnow() > expiry - timedelta(minutes=5):
        _refresh_token()
    return st.session_state.get("google_access_token")


def build_auth_url() -> str:
    """Build the Google OAuth authorization URL."""
    state = base64.urlsafe_b64encode(os.urandom(16)).decode()
    st.session_state["oauth_state"] = state

    params = {
        "client_id":     get_client_id(),
        "redirect_uri":  get_redirect_uri(),
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(code: str) -> bool:
    """Exchange authorization code for access + refresh tokens."""
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     get_client_id(),
            "client_secret": get_client_secret(),
            "redirect_uri":  get_redirect_uri(),
            "grant_type":    "authorization_code",
        }, timeout=10)
        resp.raise_for_status()
        _store_tokens(resp.json())
        return True
    except Exception as e:
        st.error(f"OAuth token exchange failed: {e}")
        return False


def _refresh_token():
    refresh = st.session_state.get("google_refresh_token")
    if not refresh:
        return
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "refresh_token": refresh,
            "client_id":     get_client_id(),
            "client_secret": get_client_secret(),
            "grant_type":    "refresh_token",
        }, timeout=10)
        resp.raise_for_status()
        _store_tokens(resp.json())
    except Exception:
        # Force re-auth if refresh fails
        st.session_state.pop("google_access_token", None)


def _store_tokens(data: dict):
    st.session_state["google_access_token"]  = data["access_token"]
    st.session_state["google_token_expiry"]  = (
        datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
    )
    if "refresh_token" in data:
        st.session_state["google_refresh_token"] = data["refresh_token"]
    if "id_token" in data:
        # Decode user info from id_token (no verification needed here — display only)
        try:
            payload = data["id_token"].split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            info = json.loads(base64.urlsafe_b64decode(payload))
            st.session_state["google_user_name"]  = info.get("name", "")
            st.session_state["google_user_email"] = info.get("email", "")
        except Exception:
            pass


def sign_out():
    token = st.session_state.get("google_access_token")
    if token:
        try:
            requests.post(GOOGLE_REVOKE_URL, params={"token": token}, timeout=5)
        except Exception:
            pass
    for key in ["google_access_token", "google_refresh_token", "google_token_expiry",
                "google_user_name", "google_user_email", "oauth_state"]:
        st.session_state.pop(key, None)
