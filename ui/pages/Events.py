import streamlit as st
import requests
import json
from datetime import date, timedelta
import base64
from PIL import Image
import io

# --- Page Configuration ---
st.set_page_config(page_title="Events", layout="wide")

st.title("Events Viewer")

# --- Backend Configuration ---
# Use secrets for the API URL in deployment
API_URL = st.secrets.get("API_BASE", "http://localhost:8001")
# For local testing, you can uncomment the line below:
# API_URL = "http://localhost:8001" 

# --- User Interface for Date Selection ---
today = date.today()
start_date = st.date_input("Start date", today - timedelta(days=7))
end_date = st.date_input("End date", today)

# --- Main Logic ---
if st.button("Get Events"):
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat() + "T23:59:59",
    }
    
    try:
        # Fetch data from the backend API
        response = requests.get(f"{API_URL}/get-events", params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        events = response.json()

        if not events:
            st.warning("No events found for the selected date range.")
        else:
            st.success(f"Found {len(events)} events.")
            
            # Loop through each event and display it in an expander
            for i, event_data in enumerate(events):
                with st.expander(f"Event {i+1} - ID: {event_data.get('eventId', 'N/A')} at {event_data.get('timestamp', 'N/A')}"):
                    
                    # Separate the image data from the rest of the metadata
                    image_b64 = event_data.pop("imageBaseString", None) 
                    
                    col1, col2 = st.columns(2)

                    # Display metadata in the first column
                    with col1:
                        st.subheader("Event Metadata")
                        st.json(event_data)
                    
                    # Display the image in the second column
                    with col2:
                        st.subheader("Event Image")
                        if image_b64:
                            try:
                                # Clean the base64 string if it has a data URI prefix
                                if image_b64.startswith("data:image"):
                                    image_b64 = image_b64.split(",", 1)[1]
                                
                                # Decode the base64 string into bytes
                                img_data = base64.b64decode(image_b64)
                                
                                # Open the image from bytes and display it
                                img = Image.open(io.BytesIO(img_data))
                                st.image(img, caption="Event Image", use_container_width=True)
                                
                            except Exception as e:
                                # Handle errors during image decoding/processing
                                st.error(f"Could not display image: {e}")
                                st.warning("The image data may be corrupted or in an unsupported format.")
                        else:
                            st.info("No image available for this event.")

    # --- Error Handling for API Requests ---
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching events from the backend: {e}")
        st.error(f"Please ensure the backend server is running and accessible at: {API_URL}")
    except json.JSONDecodeError:
        st.error("Failed to decode JSON from the response. The backend might have returned an error page.")
        # Only show raw response if available for troubleshooting
        if 'response' in locals():
            st.code(f"Raw Response (first 500 chars):\n{response.text[:500]}", language=None)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
