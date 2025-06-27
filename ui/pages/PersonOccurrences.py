import streamlit as st
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image
from utils.api_logger import logged_request
from utils.setup import global_page_setup

st.set_page_config(page_title="Person Occurrences", layout="wide")

API_URL = st.secrets.get("API_BASE", "http://localhost:8001")

st.title("Person Occurrences")
query_params = st.query_params
person_id = query_params.get("personId", None)

if not person_id:
    st.error("No personId provided")
    st.stop()

st.markdown(f"### All occurrences for Person ID: `{person_id}`")
st.write("")

with st.sidebar:
    st.header("Filter Options")
    start_date = st.date_input("Start Date", value=None, key="person_start_date")
    end_date = st.date_input("End Date", value=None, key="person_end_date")
    fetch_btn = st.button("Apply Filters")

params = {"personId": person_id}

if start_date:
    params["start_date"] = datetime.combine(start_date, datetime.min.time()).isoformat()
if end_date:
    params["end_date"] = datetime.combine(end_date, datetime.max.time()).isoformat()

if "person_events" not in st.session_state or fetch_btn:
    with st.spinner("Loading person occurrences..."):
        try:
            resp = logged_request("get", f"{API_URL}/get-appearances", params=params)
            resp.raise_for_status()
            person_events = resp.json()
            st.session_state["person_events"] = person_events
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            st.session_state["person_events"] = []
    
events = st.session_state.get("person_events", [])

if not events:
    st.warning("No occurrences found for this person with the current filters.")
else:
    unique_sites = sorted(set(event.get("siteName", "Unknown") for event in events if event.get("siteName")))
    selected_site = "All Sites"
    if unique_sites:
        col1, col2 = st.columns([2,4])
        with col1:
            selected_site = st.selectbox(
                "Filter by Site", 
                options=["All Sites"] + unique_sites,
                index=0,
                key="site_filter"
            )
        with col2:
            col1, col2 = st.columns(2)
            with col1:
                events_for_metrics = events if selected_site == "All Sites" else [event for event in events if event.get("siteName") == selected_site]
                st.metric("Total Occurrences", len(events_for_metrics))
            with col2:
                st.metric("Unique Sites", len(unique_sites))
    
    if selected_site != "All Sites":
        events = [event for event in events if event.get("siteName") == selected_site]
    
    events = sorted(events, key=lambda x: x.get("eventStartTime", ""), reverse=True)
    
    st.divider()

    for event in events:
        col1, col2 = st.columns(2, gap="medium")
        with col1:
            img_b64 = event.get("imageBaseString")
            if img_b64:
                try:
                    img_bytes = base64.b64decode(img_b64)
                    image = Image.open(BytesIO(img_bytes))
                    st.image(image, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not display image: {e}")
            else:
                st.write("No image available")
        
        with col2:
            event_time = event.get("eventStartTime", "Unknown Time")
            site = event.get("siteName", "Unknown Site")
            camera_id = event.get("cameraId", "Unknown Camera")
            confidence = event.get("personFace", {}).get("Confidence", 0)
            st.write(f"**Time:** {event_time[:23] if event_time else 'Unknown'}Z")
            st.write(f"**Site:** {site}")
            st.write(f"**Camera:** {camera_id}")
            st.write(f"**Confidence:** {confidence:.1f}%")
        st.divider()

global_page_setup()