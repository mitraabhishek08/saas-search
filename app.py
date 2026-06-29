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

# ─── Global CSS ───────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --primary:      #2563eb;
  --primary-dark: #1d4ed8;
  --primary-lt:   #eff6ff;
  --bg:           #f1f5f9;
  --surface:      #ffffff;
  --text:         #0f172a;
  --muted:        #64748b;
  --border:       #e2e8f0;
  --shadow-sm:    0 1px 3px rgba(0,0,0,.07), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:    0 4px 16px rgba(0,0,0,.08);
  --radius:       10px;
  --success-bg:   #dcfce7;
  --success-fg:   #15803d;
  --danger-bg:    #fee2e2;
  --danger-fg:    #b91c1c;
  --warning-bg:   #fef3c7;
  --warning-fg:   #92400e;
}

/* ── Streamlit chrome ─────────────────────────────────────────── */
#MainMenu, footer { visibility: hidden !important; }
header[data-testid="stHeader"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Base font ────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── Inputs ───────────────────────────────────────────────────── */
div[data-testid="stTextInput"] > label {
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  color: var(--text) !important;
  letter-spacing: 0.1px !important;
  margin-bottom: 4px !important;
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
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
  outline: none !important;
}

/* ── Buttons ──────────────────────────────────────────────────── */
div[data-testid="stFormSubmitButton"] > button,
div[data-testid="stButton"] > button {
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.87rem !important;
  transition: all .15s !important;
}
div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
  background: var(--primary) !important;
  border-color: var(--primary) !important;
  color: #fff !important;
}
div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"]:hover {
  background: var(--primary-dark) !important;
  box-shadow: 0 4px 14px rgba(37,99,235,.35) !important;
  transform: translateY(-1px) !important;
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
}
div[data-testid="stExpander"] > details > summary:hover {
  background: #f8fafc !important;
}

/* ── Code blocks ──────────────────────────────────────────────── */
.stCodeBlock { border-radius: 8px !important; }
.stCodeBlock code { font-size: 11.5px !important; line-height: 1.6 !important; }

/* ── Alerts ───────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
  border-radius: 8px !important;
  font-size: 0.88rem !important;
  border-left-width: 3px !important;
}

/* ── Dataframe ────────────────────────────────────────────────── */
div[data-testid="stDataFrame"] {
  border-radius: var(--radius) !important;
  overflow: hidden !important;
  box-shadow: var(--shadow-sm) !important;
}

/* ── Dividers ─────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Caption / small text ─────────────────────────────────────── */
div[data-testid="stCaptionContainer"] p {
  color: var(--muted) !important;
  font-size: 0.82rem !important;
}

/* ── Spinner ──────────────────────────────────────────────────── */
div[data-testid="stSpinner"] p {
  font-size: 0.87rem !important;
  color: var(--muted) !important;
}
</style>
"""

LOGIN_CSS = """
<style>
.stApp {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #0f172a 100%) !important;
}
[data-testid="stForm"] {
  background: white !important;
  border-radius: 16px !important;
  padding: 2rem 2.25rem !important;
  box-shadow: 0 24px 64px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.06) !important;
  border: none !important;
}
/* On login page make label text dark (card is white) */
div[data-testid="stTextInput"] > label { color: #0f172a !important; }
</style>
"""

SEARCH_CSS = """
<style>
.stApp { background: #f1f5f9 !important; }
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

# ─── Components ───────────────────────────────────────────────────────────────

def render_navbar(username: str) -> None:
    st.markdown(f"""
    <div style="
        background:#fff;
        border-bottom:1px solid #e2e8f0;
        padding:0 2rem;
        height:56px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        box-shadow:0 1px 3px rgba(0,0,0,.06);
        margin-bottom:0;
    ">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="
          width:30px;height:30px;border-radius:8px;
          background:#2563eb;
          display:flex;align-items:center;justify-content:center;
          color:#fff;font-weight:800;font-size:14px;letter-spacing:-0.5px;
        ">M</div>
        <span style="font-weight:700;font-size:1rem;color:#0f172a;letter-spacing:-0.3px;">MDM Search</span>
        <span style="
          background:#f1f5f9;border:1px solid #e2e8f0;
          border-radius:20px;padding:2px 10px;
          font-size:0.72rem;font-weight:600;color:#64748b;letter-spacing:0.2px;
          margin-left:4px;
        ">Informatica C360</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="
          background:#f1f5f9;border:1px solid #e2e8f0;
          border-radius:20px;padding:4px 14px;
          font-size:0.82rem;font-weight:500;color:#0f172a;
        ">⬤&nbsp; {username}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_api_pane() -> None:
    st.markdown("""
    <p style="font-size:.72rem;font-weight:700;text-transform:uppercase;
              letter-spacing:.7px;color:#94a3b8;margin:0 0 .6rem;">
      API Debug
    </p>""", unsafe_allow_html=True)

    if not st.session_state.api_logs:
        st.caption("No API calls yet.")
        return

    for i, log in enumerate(st.session_state.api_logs):
        ok    = isinstance(log["status"], int) and log["status"] < 400
        badge = (
            f'<span style="background:#dcfce7;color:#15803d;border-radius:4px;'
            f'padding:1px 6px;font-size:.75rem;font-weight:700;">{log["status"]}</span>'
            if ok else
            f'<span style="background:#fee2e2;color:#b91c1c;border-radius:4px;'
            f'padding:1px 6px;font-size:.75rem;font-weight:700;">{log["status"]}</span>'
        )
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


def render_results(data) -> None:
    import pandas as pd

    records, total = _extract_records(data)

    # ── Results count badge ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem;">
      <span style="font-size:.75rem;font-weight:700;text-transform:uppercase;
                   letter-spacing:.5px;color:#64748b;">Results</span>
      <span style="background:#eff6ff;color:#2563eb;border-radius:20px;
                   padding:2px 10px;font-size:.78rem;font-weight:700;">
        {total} found
      </span>
      <span style="font-size:.75rem;color:#94a3b8;">·  c360.organization</span>
    </div>
    """, unsafe_allow_html=True)

    if not records:
        st.info("No results matched your query.")
        return

    # ── Build table rows (no Score column) ───────────────────────────────────
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
            return "background-color:#dcfce7;color:#15803d;font-weight:600;border-radius:4px"
        if val in ("INACTIVE", "DELETED"):
            return "background-color:#fee2e2;color:#b91c1c;font-weight:600;border-radius:4px"
        return "color:#64748b"

    def _style_validation(val):
        if val == "PASSED":
            return "background-color:#dcfce7;color:#15803d;font-weight:600;border-radius:4px"
        if val == "FAILED":
            return "background-color:#fee2e2;color:#b91c1c;font-weight:600;border-radius:4px"
        return "color:#64748b"

    styled = (
        df.style
        .map(_style_status,    subset=["Status"])
        .map(_style_validation, subset=["Validation"])
        .set_properties(**{"font-size": "13px"})
    )

    # ── White card wrapper ────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border-radius:10px;border:1px solid #e2e8f0;
                padding:1px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:1.25rem;">
    """, unsafe_allow_html=True)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw JSON per record ───────────────────────────────────────────────────
    st.markdown("""
    <p style="font-size:.75rem;font-weight:700;text-transform:uppercase;
              letter-spacing:.5px;color:#64748b;margin:1.25rem 0 .5rem;">
      Record Details
    </p>""", unsafe_allow_html=True)

    for rec in records:
        meta   = rec.get("_meta") or {}
        name   = rec.get("c360organization.name") or meta.get("businessId") or "—"
        biz_id = meta.get("businessId") or "—"
        status = meta.get("status", "")
        color  = "#15803d" if status == "ACTIVE" else "#b91c1c" if status else "#64748b"
        label  = f"{name}   {biz_id}"
        with st.expander(label):
            st.markdown(
                f'<span style="background:{"#dcfce7" if status=="ACTIVE" else "#fee2e2"};'
                f'color:{color};border-radius:20px;padding:2px 10px;'
                f'font-size:.75rem;font-weight:700;">{status}</span>',
                unsafe_allow_html=True,
            )
            st.json(rec)

# ─── Pages ────────────────────────────────────────────────────────────────────

def page_login() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(LOGIN_CSS,  unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        # Logo + title above the form card
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.5rem;margin-top:3.5rem;">
          <div style="
            width:48px;height:48px;border-radius:12px;
            background:#2563eb;
            display:inline-flex;align-items:center;justify-content:center;
            color:#fff;font-weight:800;font-size:22px;
            box-shadow:0 8px 24px rgba(37,99,235,.45);
            margin-bottom:1rem;
          ">M</div>
          <h2 style="color:#fff;font-size:1.6rem;font-weight:800;
                     letter-spacing:-0.5px;margin:0 0 6px;">MDM Search</h2>
          <p style="color:#94a3b8;font-size:.88rem;margin:0;">
            Informatica C360 / IDMC
          </p>
        </div>
        """, unsafe_allow_html=True)

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
    st.markdown(GLOBAL_CSS,  unsafe_allow_html=True)
    st.markdown(SEARCH_CSS,  unsafe_allow_html=True)

    render_navbar(st.session_state.username)

    # ── Content area ──────────────────────────────────────────────────────────
    st.markdown("<div style='padding:1.75rem 2rem 0;'>", unsafe_allow_html=True)

    # ── Search card ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border-radius:10px;border:1px solid #e2e8f0;
                padding:1.25rem 1.5rem 0.25rem;
                box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:1.25rem;">
      <p style="font-size:.72rem;font-weight:700;text-transform:uppercase;
                letter-spacing:.5px;color:#64748b;margin:0 0 .5rem;">
        Search Organizations
      </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("search_form", clear_on_submit=False):
        q_col, btn_col, toggle_col = st.columns([6, 1, 1])
        with q_col:
            query = st.text_input(
                "query",
                value=st.session_state.search_query,
                placeholder="e.g. Walt Disney",
                label_visibility="collapsed",
            )
        with btn_col:
            search_clicked = st.form_submit_button("Search", use_container_width=True)
        with toggle_col:
            # Can't use a regular button inside a form; use secondary submit
            toggle_clicked = st.form_submit_button(
                "Hide API" if st.session_state.show_api_pane else "Show API",
                use_container_width=True,
            )

    if toggle_clicked:
        st.session_state.show_api_pane = not st.session_state.show_api_pane
        st.rerun()

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

    # ── Footer / logout ───────────────────────────────────────────────────────
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    _, _, logout_col = st.columns([5, 1, 1])
    with logout_col:
        if st.button("Log out", use_container_width=True, key="logout"):
            for k, v in _DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ─── Router ───────────────────────────────────────────────────────────────────
if st.session_state.session_id:
    page_search()
else:
    page_login()
