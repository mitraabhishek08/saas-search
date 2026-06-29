import re
import json
import os
from datetime import datetime

import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MDM Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stExpander"] {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-bottom: 6px;
    }
    .stCodeBlock code { font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "session_id":    None,
    "base_api_url":  None,
    "username":      None,
    "show_api_pane": False,
    "api_logs":      [],
    "search_results": None,
    "search_query":  "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── MDM API ──────────────────────────────────────────────────────────────────

def _search_host(base_api_url: str) -> str:
    # Mirrors MCP mdmHost(): prepend usw1-mdm. to the hostname
    return re.sub(r"^(https?://)([^/]+)", r"\1usw1-mdm.\2", base_api_url.rstrip("/"))


def _log(method: str, url: str, req: dict, status, resp) -> None:
    st.session_state.api_logs.insert(0, {
        "ts":       datetime.now().strftime("%H:%M:%S"),
        "method":   method,
        "url":      url,
        "request":  req,
        "status":   status,
        "response": resp,
    })
    st.session_state.api_logs = st.session_state.api_logs[:10]


def mdm_login(pod_url: str, username: str, password: str):
    url     = f"{pod_url.rstrip('/')}/saas/public/core/v3/login"
    payload = {"username": username, "password": password}
    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        _log("POST", url, {**payload, "password": "***"}, r.status_code, data)

        ui = data.get("userInfo") or {}
        session_id   = data.get("icSessionId") or ui.get("icSessionId") or data.get("sessionId") or ui.get("sessionId") or ""
        base_api_url = data.get("baseApiUrl")  or ui.get("baseApiUrl")  or pod_url

        if not session_id:
            return None, None, f"No session ID found. Response keys: {list(data.keys())}"
        return session_id, base_api_url, None

    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response else str(e)
        _log("POST", url, {**payload, "password": "***"}, getattr(e.response, "status_code", "ERR"), body)
        return None, None, f"HTTP {getattr(e.response, 'status_code', '?')}: {body}"
    except Exception as e:
        _log("POST", url, {**payload, "password": "***"}, "ERR", str(e))
        return None, None, str(e)


def mdm_search(query: str, session_id: str, base_api_url: str):
    url     = f"{_search_host(base_api_url)}/search/public/api/v1/search"
    payload = {
        "entityType":      "c360.organization",
        "search":          query,
        "recordsToReturn": 25,
        "recordOffset":    0,
    }
    headers = {
        "IDS-SESSION-ID": session_id,
        "Content-Type":   "application/json",
        "Accept":         "application/json",
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        _log("POST", url, payload, r.status_code, data)
        return data, None

    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response else str(e)
        _log("POST", url, payload, getattr(e.response, "status_code", "ERR"), body)
        return None, f"HTTP {getattr(e.response, 'status_code', '?')}: {body}"
    except Exception as e:
        _log("POST", url, payload, "ERR", str(e))
        return None, str(e)

# ─── Components ───────────────────────────────────────────────────────────────

def render_api_pane() -> None:
    st.markdown("#### API Debug")
    if not st.session_state.api_logs:
        st.caption("No API calls yet — log in or run a search.")
        return

    for i, log in enumerate(st.session_state.api_logs):
        ok   = isinstance(log["status"], int) and log["status"] < 400
        icon = "✅" if ok else "❌"
        # Short path label for the expander title
        path_tail = log["url"].rsplit("/", 1)[-1]
        label = f"{icon} {log['ts']}  ·  {log['method']} /{path_tail}  ·  {log['status']}"

        with st.expander(label, expanded=(i == 0)):
            st.markdown("**URL**")
            st.code(f"{log['method']} {log['url']}", language="http")

            st.markdown("**Request body**")
            st.code(json.dumps(log["request"], indent=2), language="json")

            resp_str = (
                json.dumps(log["response"], indent=2)
                if isinstance(log["response"], (dict, list))
                else str(log["response"])
            )
            st.markdown(f"**Response** — `{log['status']}`")
            st.code(resp_str, language="json")


def render_results(data) -> None:
    if isinstance(data, dict):
        entities = (
            data.get("searchResults") or
            data.get("results")       or
            data.get("entities")      or
            data.get("data")          or []
        )
        total = data.get("totalCount") or data.get("total") or len(entities)
    elif isinstance(data, list):
        entities, total = data, len(data)
    else:
        st.warning("Unexpected response format.")
        st.json(data)
        return

    st.caption(f"**{total}** result(s) · entity type `c360.organization`")

    if not entities:
        st.info("No results found.")
        return

    for entity in entities:
        inner = entity.get("data") or {}
        name = (
            entity.get("label")       or
            inner.get("fullName")     or
            inner.get("name")         or
            entity.get("displayName") or
            entity.get("name")        or
            entity.get("businessId")  or "—"
        )
        biz_id = entity.get("businessId") or entity.get("id") or "—"
        score  = entity.get("score")
        score_str = f"  ·  score {score:.2f}" if score is not None else ""

        with st.expander(f"**{name}**  `{biz_id}`{score_str}"):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Business ID**  \n`{biz_id}`")
            c2.markdown(f"**Entity Type**  \n`{entity.get('entityType', 'c360.organization')}`")
            if score is not None:
                c3.markdown(f"**Match Score**  \n`{score:.4f}`")
            st.divider()
            st.json(entity)

# ─── Pages ────────────────────────────────────────────────────────────────────

def page_login() -> None:
    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        st.markdown("## MDM Search")
        st.caption("Informatica C360 / IDMC")
        st.divider()

        with st.form("login_form"):
            pod_url  = st.text_input(
                "Pod URL",
                value=os.getenv("IDMC_POD_URL", "https://dmp-us.informaticacloud.com"),
                help="IDMC pod base URL, e.g. https://dmp-us.informaticacloud.com",
            )
            username = st.text_input("Username", value=os.getenv("IDMC_USERNAME", ""))
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Username and password are required.")
            else:
                with st.spinner("Signing in…"):
                    sid, base_url, err = mdm_login(pod_url, username, password)
                if err:
                    st.error(err)
                else:
                    st.session_state.session_id   = sid
                    st.session_state.base_api_url = base_url
                    st.session_state.username     = username
                    st.rerun()

        # Show login API call in debug area below the form
        if st.session_state.api_logs:
            st.divider()
            render_api_pane()


def page_search() -> None:
    # ── Top bar ───────────────────────────────────────────────────────────────
    top_left, top_right = st.columns([6, 1])
    with top_left:
        st.markdown("## MDM Organization Search")
        st.caption(f"Signed in as **{st.session_state.username}**")
    with top_right:
        st.write("")  # vertical alignment nudge
        pane_label = "Hide API" if st.session_state.show_api_pane else "Show API"
        if st.button(pane_label, use_container_width=True, key="toggle_pane"):
            st.session_state.show_api_pane = not st.session_state.show_api_pane
            st.rerun()

    # ── Search bar ────────────────────────────────────────────────────────────
    with st.form("search_form", clear_on_submit=False):
        q_col, btn_col = st.columns([6, 1])
        with q_col:
            query = st.text_input(
                "query",
                value=st.session_state.search_query,
                placeholder="Search organizations — e.g. Walt Disney",
                label_visibility="collapsed",
            )
        with btn_col:
            search_clicked = st.form_submit_button("Search", use_container_width=True)

    if search_clicked and query:
        st.session_state.search_query = query
        with st.spinner("Searching…"):
            data, err = mdm_search(query, st.session_state.session_id, st.session_state.base_api_url)
        if err:
            st.error(err)
            st.session_state.search_results = None
        else:
            st.session_state.search_results = data

    # ── Body ──────────────────────────────────────────────────────────────────
    if st.session_state.show_api_pane:
        left, right = st.columns([3, 2], gap="large")
        with left:
            if st.session_state.search_results is not None:
                render_results(st.session_state.search_results)
        with right:
            render_api_pane()
    else:
        if st.session_state.search_results is not None:
            render_results(st.session_state.search_results)

    # ── Logout ────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("Log out", key="logout"):
        for k, v in _DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

# ─── Router ───────────────────────────────────────────────────────────────────
if st.session_state.session_id:
    page_search()
else:
    page_login()
