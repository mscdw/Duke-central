import streamlit as st
import base64
from datetime import datetime, date
from utils.api_logger import logged_request
from utils.setup import global_page_setup
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Appearance Events", layout="wide")
st.title("Appearance Events")

API_URL = st.secrets.get("API_BASE", "http://localhost:8001")

with st.sidebar:
    st.header("Fetch Events")
    today = date.today()
    start_dt = st.date_input("Start date", value=today, key="start_dt")
    start_time = st.time_input("Start time", value=datetime.min.time(), key="start_time")
    end_dt = st.date_input("End date", value=today, key="end_dt")
    end_time = st.time_input("End time", value=datetime.max.time().replace(microsecond=0), key="end_time")
    fetch_btn = st.button("Fetch Events")

if "events" not in st.session_state:
    st.session_state["events"] = []
if "site_options" not in st.session_state:
    st.session_state["site_options"] = ["All"]

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

if fetch_btn:
    try:
        with st.spinner("Fetching appearance events..."):
            resp = logged_request("get", f"{API_URL}/get-appearances", params=params)
            resp.raise_for_status()
            events = resp.json()
            st.session_state["events"] = events
            sites = sorted({e.get("siteName", "") for e in events if e.get("siteName")})
            st.session_state["site_options"] = ["All"] + sites if sites else ["All"]
    except Exception as e:
        st.error(f"Error fetching events: {e}")

with st.sidebar:
    st.header("Filter Results")
    selected_site = st.selectbox("Site", st.session_state["site_options"], key="site_filter")
    only_personid = st.checkbox("Only events with personId", key="personid_filter")

filtered_events = st.session_state["events"]
if selected_site and selected_site != "All":
    filtered_events = [e for e in filtered_events if e.get("siteName") == selected_site]
if only_personid:
    filtered_events = [e for e in filtered_events if e.get("personId") not in (None, "")]

total_events = len(filtered_events)
st.subheader(f"Total events: {total_events}")

if not filtered_events:
    st.info("No appearance events found.")
else:
    for idx, event in enumerate(filtered_events):
        st.markdown(f"### Event {idx+1}")
        cols = st.columns(2)
        with cols[0]:
            st.json({
                "personId": event.get("personId"),
                "objectId": event.get("objectId"),
                "confidence": event.get("confidence"),
                "generatorId": event.get("generatorId"),
                "cameraId": event.get("cameraId"),
                "eventStartTime": event.get("eventStartTime"),
                "eventEndTime": event.get("eventEndTime"),
                "snapshots": event.get("snapshots"),
                "siteName": event.get("siteName"),
                "personFace": event.get("personFace"),
            })
        with cols[1]:
            img_b64 = event.get("imageBaseString")
            if img_b64:
                try:
                    img_bytes = base64.b64decode(img_b64)
                    image = Image.open(BytesIO(img_bytes))
                    st.image(image, caption="Event Image")
                    person_face = event.get("personFace")
                    if person_face and person_face.get("BoundingBox"):
                        bbox = person_face["BoundingBox"]
                        width, height = image.size
                        left = int(bbox["Left"] * width)
                        top = int(bbox["Top"] * height)
                        right = int((bbox["Left"] + bbox["Width"]) * width)
                        bottom = int((bbox["Top"] + bbox["Height"]) * height)
                        cropped_face = image.crop((left, top, right, bottom))
                        st.image(cropped_face, caption="Cropped Face")
                except Exception as e:
                    st.warning(f"Could not decode or process image: {e}")
            else:
                st.info("No image available for this event.")

global_page_setup()
