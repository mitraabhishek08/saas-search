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

st.set_page_config(
    page_title="MDM Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Shared base (strip Streamlit chrome & wrappers) ──────────────────────────
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html { height: 100%; }

/* ── Strip ALL Streamlit backgrounds ────────────────────────── */
[data-testid] { background-color: transparent !important; }
.stApp,
.stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="stMainBlockContainer"] > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stDecoration"],
div[data-testid="stColumn"],
.main, section.main, div.main, .main > div,
.appview-container, .css-1d391kg, .css-18e3th9 {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
}

/* ── Hide Streamlit chrome ───────────────────────────────────── */
#MainMenu, footer { visibility: hidden !important; }
header[data-testid="stHeader"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Fonts ───────────────────────────────────────────────────── */
html, body, [class*="css"], p, span, label, div {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Navbar column alignment (shared) ───────────────────────── */
div[data-testid="stHorizontalBlock"]:first-of-type {
  align-items: center !important;
  padding: 0 2rem !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"] {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  min-height: 58px !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"] > div,
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"] > div > div {
  display: flex !important;
  align-items: center !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  width: 100% !important;
}

/* ── Search row: input + button vertically aligned ───────────── */
[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
  align-items: center !important;
}
[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
  display: flex !important;
  align-items: center !important;
}
[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div {
  width: 100% !important;
  min-width: 0 !important;
  margin-bottom: 0 !important;
}
[data-testid="stForm"] div[data-testid="stFormSubmitButton"] {
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
}
/* Force text input to fill its column at every nesting level */
[data-testid="stForm"] div[data-testid="stColumn"] div[data-testid="stTextInput"],
[data-testid="stForm"] div[data-testid="stColumn"] div[data-testid="stTextInput"] > div,
[data-testid="stForm"] div[data-testid="stColumn"] div[data-testid="stTextInput"] > div > div,
[data-testid="stForm"] div[data-testid="stColumn"] div[data-testid="stTextInput"] input {
  width: 100% !important;
  min-width: 0 !important;
}

/* ── Submit button — orange (always) ─────────────────────────── */
div[data-testid="stFormSubmitButton"] button {
  background: linear-gradient(135deg, #f97316, #ea580c) !important;
  border: none !important;
  color: #fff !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  box-shadow: 0 2px 12px rgba(249,115,22,0.4) !important;
  transition: all .2s !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
  box-shadow: 0 4px 20px rgba(249,115,22,0.65) !important;
  transform: translateY(-1px) !important;
}

/* ── Expander summary: fix arrow/label overlap ───────────────── */
div[data-testid="stExpander"] details summary {
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 8px !important;
  cursor: pointer !important;
  list-style: none !important;
}
div[data-testid="stExpander"] details summary > svg,
div[data-testid="stExpander"] details summary > span > svg {
  flex-shrink: 0 !important;
  order: 0 !important;
}
div[data-testid="stExpander"] details summary > div,
div[data-testid="stExpander"] details summary > p,
div[data-testid="stExpander"] details summary > span:not(:has(svg)) {
  flex: 1 !important;
  margin: 0 !important;
  min-width: 0 !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

/* ── Code blocks ─────────────────────────────────────────────── */
.stCodeBlock { border-radius: 10px !important; }
.stCodeBlock code { font-size: 11.5px !important; line-height: 1.6 !important; }

/* ── Divider ─────────────────────────────────────────────────── */
hr { border-color: #e2e8f0 !important; }
</style>
"""

# ─── Dark theme (login page) ──────────────────────────────────────────────────
DARK_CSS = _BASE_CSS + """
<style>
body {
  min-height: 100vh;
  background: linear-gradient(135deg, #020b18 0%, #051e3e 45%, #0a2a52 100%) fixed !important;
}
html, body, [class*="css"], p, span, label, div { color: rgba(220,235,255,0.9); }

/* Navbar */
div[data-testid="stHorizontalBlock"]:first-of-type {
  backdrop-filter: blur(20px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
  background: rgba(5,30,70,0.55) !important;
  border-bottom: 1px solid rgba(56,165,248,0.18) !important;
  box-shadow: 0 4px 24px rgba(0,0,0,0.35) !important;
}
/* Logout button */
div[data-testid="stHorizontalBlock"]:first-of-type
  > div[data-testid="stColumn"]:last-child
  div[data-testid="stButton"] > button {
  background: rgba(56,165,248,0.1) !important;
  border: 1px solid rgba(56,165,248,0.3) !important;
  color: rgba(148,210,255,0.8) !important;
  border-radius: 50% !important;
  width: 34px !important; height: 34px !important;
  min-height: 34px !important; padding: 0 !important;
  font-size: 15px !important; backdrop-filter: blur(8px) !important;
  transition: all .2s !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type
  > div[data-testid="stColumn"]:last-child
  div[data-testid="stButton"] > button:hover {
  background: rgba(56,165,248,0.22) !important;
  border-color: rgba(56,165,248,0.6) !important;
  color: #93c5fd !important;
  box-shadow: 0 0 16px rgba(56,165,248,0.35) !important;
}

/* Login form card */
[data-testid="stForm"] {
  backdrop-filter: blur(20px) saturate(160%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
  background: rgba(8,25,60,0.5) !important;
  border: 1px solid rgba(56,165,248,0.2) !important;
  border-radius: 20px !important;
  box-shadow: 0 8px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(56,165,248,0.12) !important;
}
div[data-testid="stTextInput"] > label {
  font-size: 0.78rem !important; font-weight: 600 !important;
  color: rgba(148,210,255,0.65) !important;
  letter-spacing: 0.3px !important; text-transform: uppercase !important;
}
div[data-testid="stTextInput"] input {
  background: rgba(5,25,65,0.6) !important;
  border: 1px solid rgba(56,165,248,0.25) !important;
  border-radius: 10px !important;
  color: rgba(220,235,255,0.95) !important;
  font-size: 0.9rem !important; transition: all .2s !important;
}
div[data-testid="stTextInput"] input::placeholder { color: rgba(148,210,255,0.28) !important; }
div[data-testid="stTextInput"] input:focus {
  background: rgba(5,25,65,0.8) !important;
  border-color: rgba(56,165,248,0.65) !important;
  box-shadow: 0 0 0 3px rgba(56,165,248,0.15) !important;
  outline: none !important;
}
div[data-testid="stAlert"] {
  background: rgba(5,20,50,0.45) !important;
  border: 1px solid rgba(56,165,248,0.18) !important;
  border-radius: 10px !important;
  backdrop-filter: blur(8px) !important;
  color: rgba(220,235,255,0.9) !important;
}
</style>
"""

# ─── Light theme (search page) ────────────────────────────────────────────────
LIGHT_CSS = _BASE_CSS + """
<style>
body {
  min-height: 100vh;
  background: #f1f5f9 !important;
  background-image: none !important;
}
html, body, [class*="css"], p, span, label, div { color: #1e293b; }

/* Navbar */
div[data-testid="stHorizontalBlock"]:first-of-type {
  background: #ffffff !important;
  border-bottom: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 8px rgba(0,0,0,0.07) !important;
}
/* Logout button */
div[data-testid="stHorizontalBlock"]:first-of-type
  > div[data-testid="stColumn"]:last-child
  div[data-testid="stButton"] > button {
  background: #f1f5f9 !important;
  border: 1px solid #e2e8f0 !important;
  color: #64748b !important;
  border-radius: 50% !important;
  width: 34px !important; height: 34px !important;
  min-height: 34px !important; padding: 0 !important;
  font-size: 15px !important;
  transition: all .2s !important;
}
div[data-testid="stHorizontalBlock"]:first-of-type
  > div[data-testid="stColumn"]:last-child
  div[data-testid="stButton"] > button:hover {
  background: #e2e8f0 !important;
  color: #334155 !important;
}

/* Search form — no outer box */
[data-testid="stForm"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  padding: 0 !important;
}
/* Inputs */
div[data-testid="stTextInput"] > label {
  font-size: 0.78rem !important; font-weight: 600 !important;
  color: #64748b !important;
  letter-spacing: 0.3px !important; text-transform: uppercase !important;
}
div[data-testid="stTextInput"] input {
  background: #ffffff !important;
  border: 1.5px solid #e2e8f0 !important;
  border-radius: 10px !important;
  color: #1e293b !important;
  font-size: 0.9rem !important; transition: all .2s !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
div[data-testid="stTextInput"] input::placeholder { color: #94a3b8 !important; }
div[data-testid="stTextInput"] input:focus {
  background: #ffffff !important;
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
  outline: none !important;
}

/* Regular buttons */
div[data-testid="stButton"] > button {
  background: #ffffff !important;
  border: 1.5px solid #e2e8f0 !important;
  color: #334155 !important;
  border-radius: 10px !important;
  font-weight: 500 !important; font-size: 0.87rem !important;
  transition: all .2s !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
div[data-testid="stButton"] > button:hover {
  background: #f8fafc !important;
  border-color: #cbd5e1 !important;
  color: #0f172a !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
}

/* Expanders */
div[data-testid="stExpander"] {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  margin-bottom: 8px !important;
  overflow: hidden !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}
div[data-testid="stExpander"] > details > summary {
  font-size: 0.85rem !important; font-weight: 500 !important;
  padding: 0.7rem 1rem !important; color: #334155 !important;
}
div[data-testid="stExpander"] > details > summary:hover {
  background: #f8fafc !important;
}

/* Dataframe */
div[data-testid="stDataFrame"] {
  background: #ffffff !important;
  border-radius: 12px !important;
  border: 1px solid #e2e8f0 !important;
  overflow: hidden !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}

/* Alerts */
div[data-testid="stAlert"] {
  background: #ffffff !important;
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  color: #1e293b !important;
}

/* Caption */
div[data-testid="stCaptionContainer"] p { color: #94a3b8 !important; }

/* Spinner */
div[data-testid="stSpinner"] p { color: #64748b !important; }

/* Divider */
hr { border-color: #e2e8f0 !important; }
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


def _log(method, url, req, status, resp):
    st.session_state.api_logs.insert(0, {
        "ts": datetime.now().strftime("%H:%M:%S"),
        "method": method, "url": url,
        "request": req, "status": status, "response": resp,
    })
    st.session_state.api_logs = st.session_state.api_logs[:10]


def mdm_login(pod_url, username, password):
    url     = f"{pod_url.rstrip('/')}/saas/public/core/v3/login"
    payload = {"username": username, "password": password}
    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        _log("POST", url, {**payload, "password": "***"}, r.status_code, data)
        ui           = data.get("userInfo") or {}
        session_id   = data.get("icSessionId") or ui.get("icSessionId") or data.get("sessionId") or ui.get("sessionId") or ""
        base_api_url = data.get("baseApiUrl") or ui.get("baseApiUrl") or pod_url
        if not session_id:
            return None, None, f"No session ID. Keys: {list(data.keys())}"
        return session_id, base_api_url, None
    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response else str(e)
        _log("POST", url, {**payload, "password": "***"}, getattr(e.response, "status_code", "ERR"), body)
        return None, None, f"HTTP {getattr(e.response, 'status_code', '?')}: {body}"
    except Exception as e:
        _log("POST", url, {**payload, "password": "***"}, "ERR", str(e))
        return None, None, str(e)


def mdm_search(query, session_id, base_api_url):
    url     = f"{_search_host(base_api_url)}/search/public/api/v1/search"
    payload = {"entityType": "c360.organization", "search": query, "recordsToReturn": 25, "recordOffset": 0}
    headers = {"IDS-SESSION-ID": session_id, "Content-Type": "application/json", "Accept": "application/json"}
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

def render_navbar(theme="dark"):
    brand_col, _, user_col, logout_col = st.columns([3, 4, 1.5, 0.25])

    if theme == "light":
        brand_color  = "#0f172a"
        badge_style  = ("background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.28);"
                        "border-radius:20px;padding:2px 10px;font-size:.7rem;font-weight:600;color:#1d4ed8;")
        chip_style   = ("background:#f1f5f9;border:1px solid #e2e8f0;border-radius:20px;"
                        "padding:5px 14px;font-size:.82rem;font-weight:500;color:#334155;white-space:nowrap;")
    else:
        brand_color  = "rgba(220,235,255,.95)"
        badge_style  = ("background:rgba(14,165,233,.15);border:1px solid rgba(14,165,233,.35);"
                        "border-radius:20px;padding:2px 10px;font-size:.7rem;font-weight:600;color:#7dd3fc;")
        chip_style   = ("background:rgba(14,165,233,.1);border:1px solid rgba(14,165,233,.28);"
                        "border-radius:20px;padding:5px 14px;font-size:.82rem;font-weight:500;"
                        "color:rgba(148,210,255,.9);white-space:nowrap;backdrop-filter:blur(8px);")

    with brand_col:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:.97rem;font-weight:700;color:{brand_color};letter-spacing:-.3px;">MDM Search</span>
          <span style="{badge_style}">Informatica C360</span>
        </div>
        """, unsafe_allow_html=True)
    with user_col:
        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;">
          <span style="{chip_style}">{st.session_state.username}</span>
        </div>
        """, unsafe_allow_html=True)
    with logout_col:
        if st.button("⏻", key="logout_nav", help="Sign out"):
            _do_logout()


def render_api_pane(theme="dark"):
    label_color = "#64748b" if theme == "light" else "rgba(255,255,255,.4)"
    st.markdown(f"""
    <p style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;
              color:{label_color};margin:0 0 .75rem;">API Debug</p>
    """, unsafe_allow_html=True)
    if not st.session_state.api_logs:
        st.caption("No API calls yet.")
        return
    for i, log in enumerate(st.session_state.api_logs):
        label = f"{log['ts']}  ·  {log['method']} /{log['url'].rsplit('/',1)[-1]}  ·  {log['status']}"
        with st.expander(label, expanded=(i == 0)):
            st.markdown("**URL**")
            st.code(f"{log['method']} {log['url']}", language="http")
            st.markdown("**Request body**")
            st.code(json.dumps(log["request"], indent=2), language="json")
            resp_str = json.dumps(log["response"], indent=2) if isinstance(log["response"], (dict, list)) else str(log["response"])
            st.markdown(f"**Response** — `{log['status']}`")
            st.code(resp_str, language="json")


def render_results(data, theme="dark"):
    import pandas as pd

    records, total = _extract_records(data)

    if theme == "light":
        label_color  = "#64748b"
        badge_style  = ("background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.28);"
                        "border-radius:20px;padding:2px 10px;font-size:.78rem;font-weight:700;color:#1d4ed8;")
    else:
        label_color  = "rgba(148,210,255,.5)"
        badge_style  = ("background:rgba(14,165,233,.15);border:1px solid rgba(14,165,233,.3);"
                        "border-radius:20px;padding:2px 10px;font-size:.78rem;font-weight:700;color:#7dd3fc;")

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:2rem 0 .75rem;">
      <span style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;
                   color:{label_color};">Organizations</span>
      <span style="{badge_style}">{total} found</span>
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
        if val == "ACTIVE":   return "background:#dcfce7;color:#166534;font-weight:600"
        if val in ("INACTIVE","DELETED"): return "background:#fee2e2;color:#991b1b;font-weight:600"
        return "color:#64748b"

    def _style_validation(val):
        if val == "PASSED": return "background:#dcfce7;color:#166534;font-weight:600"
        if val == "FAILED": return "background:#fee2e2;color:#991b1b;font-weight:600"
        return "color:#64748b"

    styled = (
        df.style
        .map(_style_status,     subset=["Status"])
        .map(_style_validation, subset=["Validation"])
        .set_properties(**{"font-size": "13px", "color": "#1e293b"})
        .set_table_styles([
            {"selector": "th", "props": [
                ("background", "#1e3a5f"),
                ("color", "#93c5fd"),
                ("font-weight", "700"),
                ("font-size", "11px"),
                ("text-transform", "uppercase"),
                ("letter-spacing", "0.5px"),
                ("border-bottom", "1px solid #2d5a8e"),
                ("padding", "10px 12px"),
            ]},
            {"selector": "td", "props": [
                ("border-bottom", "1px solid #f1f5f9"),
                ("color", "#1e293b"),
                ("padding", "10px 12px"),
            ]},
            {"selector": "tr:hover td", "props": [("background", "#f8faff")]},
        ])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ─── Pages ────────────────────────────────────────────────────────────────────

def page_login():
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.1, 1])
    with center:
        st.markdown("<div style='height:5rem'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem;">
          <p style="font-size:1.5rem;font-weight:700;color:rgba(255,255,255,.95);
                    letter-spacing:-.5px;margin:0 0 6px;">MDM Search</p>
          <p style="font-size:.85rem;color:rgba(255,255,255,.4);margin:0;">
            Informatica C360 / IDMC
          </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            pod_url  = st.text_input("Pod URL", value=os.getenv("IDMC_POD_URL", "https://dmp-us.informaticacloud.com"), help="IDMC pod base URL")
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
            render_api_pane(theme="dark")


def page_search():
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
    render_navbar(theme="light")

    st.markdown("<div style='padding:2rem 2.5rem 2rem;'>", unsafe_allow_html=True)

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

    if st.session_state.search_results is not None:
        render_results(st.session_state.search_results, theme="light")

        st.markdown("<div style='margin-top:2rem;'>", unsafe_allow_html=True)
        api_label = "Hide API Response" if st.session_state.show_api_pane else "Show API Response"
        if st.button(api_label, key="toggle_api"):
            st.session_state.show_api_pane = not st.session_state.show_api_pane
            st.rerun()

        if st.session_state.show_api_pane:
            st.markdown("<div style='margin-top:1rem;'>", unsafe_allow_html=True)
            render_api_pane(theme="light")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ─── Router ───────────────────────────────────────────────────────────────────
if st.session_state.session_id:
    page_search()
else:
    page_login()
