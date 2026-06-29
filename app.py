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

# ─── CSS ──────────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --orange:       #f97316;
  --orange-dark:  #ea580c;
  --orange-lt:    #fff7ed;
  --orange-ring:  rgba(249,115,22,.18);
  --bg:           #f8f7f5;
  --surface:      #ffffff;
  --text:         #1c1917;
  --muted:        #78716c;
  --border:       #e7e5e4;
  --shadow-sm:    0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --radius:       10px;
  --success-bg:   #dcfce7;
  --success-fg:   #15803d;
  --danger-bg:    #fee2e2;
  --danger-fg:    #b91c1c;
}

/* ── Streamlit chrome ─────────────────────────────────────────── */
#MainMenu, footer { visibility: hidden !important; }
header[data-testid="stHeader"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
body  { background: var(--bg) !important; }
.stApp { background: transparent !important; }

/* ── Navbar: first horizontal block on the page ───────────────── */
div[data-testid="stHorizontalBlock"]:first-of-type {
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 0 2rem !important;
  box-shadow: 0 1px 4px rgba(0,0,0,.05) !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"] {
  display: flex !important;
  align-items: center !important;
  min-height: 56px !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"] > div {
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  width: 100% !important;
}
/* Logout icon button — last column of navbar */
div[data-testid="stHorizontalBlock"]:first-of-type
  > div[data-testid="stColumn"]:last-child
  div[data-testid="stButton"] > button {
  background: transparent !important;
  border: 1.5px solid var(--border) !important;
  color: var(--muted) !important;
  border-radius: 50% !important;
  width: 32px !important;
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 !important;
  font-size: 15px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all .15s !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type
  > div[data-testid="stColumn"]:last-child
  div[data-testid="stButton"] > button:hover {
  border-color: var(--orange) !important;
  color: var(--orange) !important;
  background: var(--orange-lt) !important;
}

/* ── Inputs ───────────────────────────────────────────────────── */
div[data-testid="stTextInput"] > label {
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  color: var(--text) !important;
}
div[data-testid="stTextInput"] input {
  border-radius: 8px !important;
  border: 1.5px solid var(--border) !important;
  background: var(--surface) !important;
  font-size: 0.9rem !important;
  color: var(--text) !important;
  transition: border-color .15s, box-shadow .15s !important;
}
div[data-testid="stTextInput"] input:focus {
  border-color: var(--orange) !important;
  box-shadow: 0 0 0 3px var(--orange-ring) !important;
}
div[data-testid="stTextInput"] input::placeholder { color: #a8a29e !important; }

/* ── Primary submit button (Search / Sign in) ─────────────────── */
div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
  background: var(--orange) !important;
  border-color: var(--orange) !important;
  color: #fff !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.87rem !important;
  transition: all .15s !important;
}
div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"]:hover {
  background: var(--orange-dark) !important;
  box-shadow: 0 4px 14px rgba(249,115,22,.35) !important;
  transform: translateY(-1px) !important;
}
/* Regular Streamlit buttons (Show API / Hide API toggle) */
div[data-testid="stButton"] > button {
  border-radius: 8px !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  transition: all .15s !important;
}

/* ── Expanders ────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
  border-radius: 8px !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  margin-bottom: 6px !important;
  box-shadow: var(--shadow-sm) !important;
  overflow: hidden !important;
}
div[data-testid="stExpander"] > details > summary {
  font-size: 0.87rem !important;
  font-weight: 500 !important;
  padding: 0.7rem 1rem !important;
  color: var(--text) !important;
}
div[data-testid="stExpander"] > details > summary:hover { background: var(--bg) !important; }

/* ── Code blocks ──────────────────────────────────────────────── */
.stCodeBlock { border-radius: 8px !important; }
.stCodeBlock code { font-size: 11.5px !important; line-height: 1.6 !important; }

/* ── Alerts ───────────────────────────────────────────────────── */
div[data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.88rem !important; }

/* ── Dataframe ────────────────────────────────────────────────── */
div[data-testid="stDataFrame"] { border-radius: var(--radius) !important; overflow: hidden !important; }

/* ── Dividers ─────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }
</style>
"""

LOGIN_CSS = """
<style>
/* Gradient lives on body — nothing can sit above it */
body {
  background: linear-gradient(145deg, #1c0a00 0%, #7c2d12 45%, #431407 100%) fixed !important;
}
/* Every Streamlit wrapper must be transparent */
.stApp,
.stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="stMainBlockContainer"] > div,
[data-testid="stVerticalBlock"],
div[data-testid="stColumn"],
section.main,
div.main,
.main > div {
  background: transparent !important;
  background-color: transparent !important;
}
[data-testid="stForm"] {
  background: #ffffff !important;
  border-radius: 16px !important;
  padding: 2.25rem 2.5rem !important;
  box-shadow: 0 32px 80px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.06) !important;
  border: none !important;
}
div[data-testid="stTextInput"] > label { color: #1c1917 !important; }
div[data-testid="stFormSubmitButton"] > button {
  background: #f97316 !important;
  border-color: #f97316 !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
  background: #ea580c !important;
  box-shadow: 0 4px 14px rgba(249,115,22,.4) !important;
  transform: translateY(-1px) !important;
}
</style>
"""

# ─── Session State ────────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "session_id":     None,
    "base_api_url":   None,
    "username":       None,
    "show_api_pane":  False,
    "api_logs":       [],
    "search_results": None,
    "search_query":   "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── MDM API ──────────────────────────────────────────────────────────────────

def _search_host(base_api_url: str) -> str:
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
        ui           = data.get("userInfo") or {}
        session_id   = data.get("icSessionId") or ui.get("icSessionId") or data.get("sessionId") or ui.get("sessionId") or ""
        base_api_url = data.get("baseApiUrl")  or ui.get("baseApiUrl")  or pod_url
        if not session_id:
            return None, None, f"No session ID in response. Keys: {list(data.keys())}"
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


def _do_logout():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()


def _extract_records(data):
    if isinstance(data, list):
        return data, len(data)
    if isinstance(data, dict):
        sr = data.get("searchResult") or {}
        if sr.get("records") is not None:
            return sr["records"], sr.get("hits", len(sr["records"]))
        for key in ("searchResults", "results", "entities", "records"):
            if data.get(key) is not None:
                recs = data[key]
                return recs, data.get("hits") or data.get("totalCount") or data.get("total") or len(recs)
    return [], 0

# ─── Components ───────────────────────────────────────────────────────────────

def render_navbar() -> None:
    brand_col, _, user_col, logout_col = st.columns([3, 4, 1.5, 0.25])

    with brand_col:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:.97rem;font-weight:700;color:#1c1917;letter-spacing:-.3px;">
            MDM Search
          </span>
          <span style="
            background:#fff7ed;border:1px solid #fed7aa;border-radius:20px;
            padding:2px 10px;font-size:.7rem;font-weight:600;color:#ea580c;
          ">Informatica C360</span>
        </div>
        """, unsafe_allow_html=True)

    with user_col:
        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;">
          <span style="
            background:#f8f7f5;border:1px solid #e7e5e4;border-radius:20px;
            padding:5px 14px;font-size:.82rem;font-weight:500;color:#1c1917;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
          ">{st.session_state.username}</span>
        </div>
        """, unsafe_allow_html=True)

    with logout_col:
        if st.button("⏻", key="logout_nav", help="Sign out"):
            _do_logout()


def render_api_pane() -> None:
    st.markdown("""
    <p style="font-size:.72rem;font-weight:700;text-transform:uppercase;
              letter-spacing:.7px;color:#a8a29e;margin:0 0 .75rem 0;">
      API Debug
    </p>""", unsafe_allow_html=True)

    if not st.session_state.api_logs:
        st.caption("No API calls yet.")
        return

    for i, log in enumerate(st.session_state.api_logs):
        ok    = isinstance(log["status"], int) and log["status"] < 400
        path  = log["url"].rsplit("/", 1)[-1]
        label = f"{log['ts']}  ·  {log['method']} /{path}  ·  {log['status']}"
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
    import pandas as pd

    records, total = _extract_records(data)

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:2rem 0 0.75rem;">
      <span style="font-size:.75rem;font-weight:700;text-transform:uppercase;
                   letter-spacing:.5px;color:#78716c;">Organizations</span>
      <span style="
        background:#fff7ed;color:#ea580c;border:1px solid #fed7aa;
        border-radius:20px;padding:2px 10px;font-size:.78rem;font-weight:700;
      ">{total} found</span>
    </div>
    """, unsafe_allow_html=True)

    if not records:
        st.info("No results matched your query.")
        return

    rows = []
    for rec in records:
        meta   = rec.get("_meta") or {}
        states = meta.get("states") or {}
        addr   = (rec.get("c360organization.PostalAddress") or [{}])[0]
        ctry   = addr.get("country") or {}
        rows.append({
            "Name":        rec.get("c360organization.name") or "—",
            "Business ID": meta.get("businessId") or "—",
            "Status":      meta.get("status") or "—",
            "Validation":  states.get("validation") or "—",
            "City":        addr.get("city") or "—",
            "Country":     ctry.get("Name") or ctry.get("Code") or "—",
            "Address":     addr.get("addressLine1") or "—",
            "Postal Code": addr.get("postalCode") or "—",
        })

    df = pd.DataFrame(rows)

    def _style_status(val):
        if val == "ACTIVE":
            return "background-color:#dcfce7;color:#15803d;font-weight:600"
        if val in ("INACTIVE", "DELETED"):
            return "background-color:#fee2e2;color:#b91c1c;font-weight:600"
        return "color:#78716c"

    def _style_validation(val):
        if val == "PASSED":
            return "background-color:#dcfce7;color:#15803d;font-weight:600"
        if val == "FAILED":
            return "background-color:#fee2e2;color:#b91c1c;font-weight:600"
        return "color:#78716c"

    styled = (
        df.style
        .map(_style_status,     subset=["Status"])
        .map(_style_validation, subset=["Validation"])
        .set_properties(**{"font-size": "13px"})
        .set_table_styles([{
            "selector": "th",
            "props": [
                ("background-color", "#fff7ed"),
                ("color", "#ea580c"),
                ("font-weight", "700"),
                ("font-size", "12px"),
                ("text-transform", "uppercase"),
                ("letter-spacing", "0.4px"),
                ("border-bottom", "2px solid #fed7aa"),
            ]
        }])
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)

# ─── Pages ────────────────────────────────────────────────────────────────────

def page_login() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(LOGIN_CSS,  unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.1, 1])
    with center:
        st.markdown("<div style='height:4rem'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            pod_url  = st.text_input(
                "Pod URL",
                value=os.getenv("IDMC_POD_URL", "https://dmp-us.informaticacloud.com"),
                help="IDMC pod base URL",
            )
            username = st.text_input("Username", value=os.getenv("IDMC_USERNAME", ""))
            password = st.text_input("Password", type="password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Sign in", use_container_width=True)

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

        if st.session_state.api_logs:
            st.divider()
            render_api_pane()


def page_search() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    render_navbar()

    # ── Content area ──────────────────────────────────────────────────────────
    st.markdown("<div style='padding:2rem 2.5rem 2rem;'>", unsafe_allow_html=True)

    # ── Search form ───────────────────────────────────────────────────────────
    with st.form("search_form", clear_on_submit=False):
        q_col, btn_col = st.columns([8, 1])
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

    # ── Results table ─────────────────────────────────────────────────────────
    if st.session_state.search_results is not None:
        render_results(st.session_state.search_results)

        # ── API toggle + pane (below table) ───────────────────────────────────
        st.markdown("<div style='margin-top:2rem;'>", unsafe_allow_html=True)

        api_label = "Hide API Response" if st.session_state.show_api_pane else "Show API Response"
        if st.button(api_label, key="toggle_api"):
            st.session_state.show_api_pane = not st.session_state.show_api_pane
            st.rerun()

        if st.session_state.show_api_pane:
            st.markdown("<div style='margin-top:1rem;'>", unsafe_allow_html=True)
            render_api_pane()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ─── Router ───────────────────────────────────────────────────────────────────
if st.session_state.session_id:
    page_search()
else:
    page_login()
