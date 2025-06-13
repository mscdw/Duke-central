import streamlit as st
import requests
import json

def ensure_log_state():
    if 'api_logs' not in st.session_state:
        st.session_state.api_logs = []

def logged_request(method, url, **kwargs):
    ensure_log_state()
    log = f"➡️ Request: {method.upper()} {url}\n"
    if 'params' in kwargs:
        log += f"🔸 Params: {json.dumps(kwargs['params'], indent=2)}\n"
    if 'json' in kwargs:
        log += f"🔸 JSON Body:\n{json.dumps(kwargs['json'], indent=2)}\n"
    st.session_state.api_logs.append(log)
    return requests.request(method, url, **kwargs)

def show_api_logs():
    ensure_log_state()
    with st.expander("🛠 Show API Request Logs", expanded=True):
        for log in st.session_state.api_logs:
            st.code(log, language="text")
