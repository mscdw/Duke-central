import streamlit as st
import base64
from datetime import datetime, date
from io import BytesIO
from PIL import Image
from utils.api_logger import logged_request

st.set_page_config(page_title="Faces Gallery", layout="wide")
st.title("Faces Gallery")

API_URL = st.secrets.get("API_BASE", "http://localhost:8001")

with st.sidebar:
    st.header("Filter by Time")
    today = date.today()
    start_dt = st.date_input("Start date", value=today, key="faces_start_dt")
    start_time = st.time_input("Start time", value=datetime.min.time(), key="faces_start_time")
    end_dt = st.date_input("End date", value=today, key="faces_end_dt")
    end_time = st.time_input("End time", value=datetime.max.time().replace(microsecond=0), key="faces_end_time")
    fetch_btn = st.button("Fetch Faces")

if "faces_events" not in st.session_state:
    st.session_state["faces_events"] = []

params = {"personIdOnly": True}
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
    with st.spinner("Loading faces..."):
        resp = logged_request("get", f"{API_URL}/get-appearances", params=params)
        resp.raise_for_status()
        st.session_state["faces_events"] = resp.json()
        st.session_state["selected_pid"] = None

events = st.session_state["faces_events"]

faces = {}
for event in events:
    pid = event.get("personId")
    if not pid:
        continue
    img_b64 = event.get("imageBaseString")
    face_img = None
    if img_b64 and event.get("personFace") and event["personFace"].get("BoundingBox"):
        try:
            img_bytes = base64.b64decode(img_b64)
            image = Image.open(BytesIO(img_bytes))
            bbox = event["personFace"]["BoundingBox"]
            width, height = image.size
            left = int(bbox["Left"] * width)
            top = int(bbox["Top"] * height)
            right = int((bbox["Left"] + bbox["Width"]) * width)
            bottom = int((bbox["Top"] + bbox["Height"]) * height)
            face_img = image.crop((left, top, right, bottom))
        except Exception:
            face_img = None
    if not face_img and img_b64:
        try:
            img_bytes = base64.b64decode(img_b64)
            face_img = Image.open(BytesIO(img_bytes))
        except Exception:
            face_img = None
    if pid not in faces and face_img:
        faces[pid] = {"image": face_img, "personId": pid}

main_cols = st.columns([2, 10])
face_keys = list(faces.keys())
if "selected_pid" not in st.session_state:
    st.session_state["selected_pid"] = None

def select_pid(pid):
    st.session_state["selected_pid"] = pid

with main_cols[0]:
    st.markdown(f"#### People ({len(face_keys)})")
    for i in range(0, len(face_keys), 2):
        row = st.columns(2)
        for j in range(2):
            if i + j < len(face_keys):
                pid = face_keys[i + j]
                caption = f"{pid}"
                if row[j].button(" ", key=f"facebtn_{pid}", help=caption):
                    select_pid(pid)
                row[j].image(faces[pid]["image"], caption=caption, use_container_width=True)

with main_cols[1]:
    if st.session_state["selected_pid"]:
        pid = st.session_state["selected_pid"]
        filtered_events = [event for event in events if event.get("personId") == pid]
        unique_sites = set(event.get("siteName", "Unknown Site") for event in filtered_events)
        st.markdown(f"### All images for personId: {pid}")
        st.markdown(f"**Total images: {len(filtered_events)} | Sites: {len(unique_sites)}**")
        for event in filtered_events:
            img_b64 = event.get("imageBaseString")
            if img_b64:
                try:
                    img_bytes = base64.b64decode(img_b64)
                    image = Image.open(BytesIO(img_bytes))
                    event_time = event.get("eventStartTime")
                    site = event.get("siteName", "Unknown Site")
                    caption = f"{event_time} | {site}"
                    st.image(image, caption=caption, use_container_width=True)
                except Exception:
                    st.warning("Could not decode image.")
    else:
        st.info("Click a face to view all images for that person.")
