import streamlit as st
import base64
from datetime import datetime, date
from utils.api_logger import logged_request
from utils.setup import global_page_setup

st.set_page_config(page_title="Appearance Events", layout="wide")
st.title("Appearance Events")

API_URL = st.secrets.get("API_BASE", "http://localhost:8001")

col1, col2 = st.columns([2, 2])
today = date.today()
with col1:
    start_dt = st.date_input("Start date", value=today, key="start_dt")
    start_time = st.time_input("Start time", value=datetime.min.time(), key="start_time")
with col2:
    end_dt = st.date_input("End date", value=today, key="end_dt")
    end_time = st.time_input("End time", value=datetime.max.time().replace(microsecond=0), key="end_time")

params = {}
if start_dt:
    if start_time:
        params["start_date"] = datetime.combine(start_dt, start_time).isoformat()
    else:
        params["start_date"] = datetime.combine(start_dt, datetime.min.time()).isoformat()
if end_dt:
    if end_time:
        params["end_date"] = datetime.combine(end_dt, end_time).isoformat()
    else:
        params["end_date"] = datetime.combine(end_dt, datetime.max.time()).isoformat()

try:
    with st.spinner("Fetching appearance events..."):
        resp = logged_request("get", f"{API_URL}/get-appearances", params=params)
        resp.raise_for_status()
        events = resp.json()
        if not events:
            st.info("No appearance events found.")
        else:
            for idx, event in enumerate(events):
                st.markdown(f"### Event {idx+1}")
                cols = st.columns(2)
                with cols[0]:
                    st.json({
                        "objectId": event.get("objectId"),
                        "confidence": event.get("confidence"),
                        "generatorId": event.get("generatorId"),
                        "cameraId": event.get("cameraId"),
                        "eventStartTime": event.get("eventStartTime"),
                        "eventEndTime": event.get("eventEndTime"),
                        "objectROI": event.get("objectROI"),
                        "objectTimeStamp": event.get("objectTimeStamp"),
                        "faceROI": event.get("faceROI"),
                        "faceTimeStamp": event.get("faceTimeStamp"),
                    })
                with cols[1]:
                    img_b64 = event.get("imageBaseString")
                    if img_b64:
                        try:
                            st.image(base64.b64decode(img_b64), caption="Event Image")
                        except Exception:
                            st.warning("Could not decode imageBaseString.")
                    else:
                        st.info("No image available for this event.")
except Exception as e:
    st.error(f"Error fetching events: {e}")

global_page_setup()
