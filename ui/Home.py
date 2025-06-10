import streamlit as st
import requests
import base64

st.set_page_config(page_title="Appearance Events", layout="wide")
st.title("Appearance Events")

API_URL = st.secrets.get("API_BASE", "http://localhost:8001/get-appearances")

try:
    with st.spinner("Fetching appearance events..."):
        resp = requests.get(API_URL)
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
