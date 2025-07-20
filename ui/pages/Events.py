import streamlit as st
import requests
import json
from datetime import date, timedelta
import base64
from PIL import Image
import io

st.set_page_config(page_title="Events", layout="wide")

st.title("Events Viewer")

# Backend URL
API_URL = st.secrets.get("API_BASE", "http://localhost:8001")

# BACKEND_URL = "http://localhost:8000/api/v1/events/get-events"

# Date range selection
today = date.today()
start_date = st.date_input("Start date", today - timedelta(days=7))
end_date = st.date_input("End date", today)

if st.button("Get Events"):
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat() + "T23:59:59",
    }
    try:
        response = requests.get(f"{API_URL}/get-events", params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        events = response.json()

        if not events:
            st.warning("No events found for the selected date range.")
        else:
            st.success(f"Found {len(events)} events.")
            for event in events:
                with st.expander(f"Event ID: {event.get('eventId', 'N/A')} at {event.get('timestamp', 'N/A')}"):
                    image_b64 = event.pop("imageBaseString", None)
                    
                    col1, col2 = st.columns(2)

                    with col1:
                        st.json(event)
                    
                    with col2:
                        if image_b64:
                            try:
                                img_data = base64.b64decode(image_b64)
                                img = Image.open(io.BytesIO(img_data))
                                st.image(img, caption="Event Image", use_column_width=True)
                            except Exception as e:
                                st.error(f"Could not display image: {e}")
                        else:
                            st.info("No image for this event.")

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching events from the backend: {e}")
    except json.JSONDecodeError:
        st.error("Failed to decode JSON from the response. The backend might have returned an error.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

