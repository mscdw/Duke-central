import streamlit as st
import requests
import json
from datetime import date, timedelta
import base64
from PIL import Image, ImageDraw, ImageFont
import io

# --- Page Configuration ---
st.set_page_config(page_title="Events", layout="wide")

st.title("Events Viewer")

# --- Backend Configuration ---
API_URL = st.secrets.get("API_BASE", "http://localhost:8001")


# --- Helper Function to Draw Bounding Boxes (NO CHANGES NEEDED HERE) ---
def draw_bounding_boxes(image: Image.Image, faces: list) -> Image.Image:
    img_with_boxes = image.convert("RGB")
    draw = ImageDraw.Draw(img_with_boxes)
    img_width, img_height = img_with_boxes.size

    font_size = max(15, int(img_height / 40))
    try:
        font = ImageFont.truetype("arial.ttf", size=font_size)
    except IOError:
        font = ImageFont.load_default()
        print("Arial font not found. Falling back to default font.")

    for i, face in enumerate(faces):
        details = face.get("rekognition_details")
        if not details or "BoundingBox" not in details:
            continue

        bbox = details["BoundingBox"]
        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        right = int(left + (bbox['Width'] * img_width))
        bottom = int(top + (bbox['Height'] * img_height))

        status = face.get("status", "unknown")
        
        if status == "matched":
            color = "#2E8B57" # SeaGreen
            label = f"MATCHED: {face.get('face_info', {}).get('FaceId', '')[:8]}..."
        elif status == "indexed":
            color = "#1E90FF" # DodgerBlue
            label = f"INDEXED: {face.get('face_info', {}).get('FaceId', '')[:8]}..."
        else:
            color = "#DC143C" # Crimson
            label = f"NOT MATCHED: {status.upper()}"

        draw.rectangle([left, top, right, bottom], outline=color, width=5)

        text_bbox = draw.textbbox((left, top), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_bg_rect = [left, top - text_height - 10, left + text_width + 10, top]
        draw.rectangle(text_bg_rect, fill=color)
        draw.text((left + 5, top - text_height - 5), label, font=font, fill="white")

    return img_with_boxes


# --- User Interface Area ---
st.subheader("1. Select Date Range")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", date.today() - timedelta(days=7))
with col2:
    end_date = st.date_input("End date", date.today())

st.subheader("2. Apply Filters")

type_options = ["DEVICE_CLASSIFIED_OBJECT_MOTION_START", "CUSTOM_APPEARANCE"]
selected_types = st.multiselect(
    "Filter by Event Type:",
    options=type_options,
    default=type_options
)

# --- START OF CHANGE ---
# 1. Added a text input for the Camera ID filter.
camera_id_filter = st.text_input("Filter by Camera ID:")
# --- END OF CHANGE ---

st.subheader("3. Filter by Face Recognition Results (Optional)")

status_options = ["matched", "indexed", "skipped_low_confidence", "error"]
col1, col2 = st.columns(2)
with col1:
    selected_statuses = st.multiselect("Filter by Face Status:", options=status_options)
    face_id_filter = st.text_input("Filter by specific Face ID:")
with col2:
    show_no_faces = st.checkbox("Show events processed with NO faces")
    show_unprocessed = st.checkbox("Show UNPROCESSED events")
    

# --- Main Logic ---
if st.button("Get Events", type="primary"):
    # Build the params dictionary to send to the API
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat() + "T23:59:59",
        "type": selected_types 
    }
    
    # --- START OF CHANGE ---
    # 2. Add the cameraId to the API request if the user provided one.
    if camera_id_filter:
        params['cameraId'] = camera_id_filter
    # --- END OF CHANGE ---
    
    if face_id_filter:
        params['faceId'] = face_id_filter
    
    try:
        # Use a placeholder for the actual API call
        # In a real scenario, this would be:
        # response = requests.get(f"{API_URL}/get-events", params=params)
        response = requests.get(f"{API_URL}/get-events", params=params)
        response.raise_for_status()
        events = response.json()

        # The API has already filtered by type, faceId, and cameraId.
        # Now, we only need to apply the remaining UI-only filters (status and checkboxes).
        if selected_statuses or show_no_faces or show_unprocessed:
            filtered_by_face_rec = []
            for event in events:
                is_match = False
                
                # Handle special checkbox filters first
                if show_unprocessed and not event.get('processed_at'):
                    filtered_by_face_rec.append(event)
                    continue
                if show_no_faces and event.get('processed_at') and not event.get('detected_faces'):
                    filtered_by_face_rec.append(event)
                    continue
                
                detected_faces = event.get('detected_faces', [])
                for face in detected_faces:
                    # Check status match
                    if selected_statuses and face.get('status') in selected_statuses:
                        is_match = True
                        break
                
                if is_match:
                    filtered_by_face_rec.append(event)
            
            # Replace the event list with the filtered list
            events = filtered_by_face_rec
        
        if not events:
            st.warning("No events found for the selected date range and filters.")
        else:
            st.success(f"Found {len(events)} events.")
            
            # The rest of the display logic requires no changes
            for i, event_data in enumerate(events):
                processed_at = event_data.get('processed_at')
                detected_faces = event_data.get('detected_faces', [])
                
                # --- START OF CHANGE ---
                # 3. Add cameraId and date to the expander title.
                camera_id = event_data.get('cameraId', 'N/A')
                event_ts = event_data.get('timestamp', 'Unknown Date')
                # Extract just the date part (YYYY-MM-DD) from the timestamp
                event_date = event_ts.split('T')[0] if 'T' in event_ts else event_ts

                expander_title = f"Camera: {camera_id} on {event_ts} - Type: {event_data.get('title')}"
                # --- END OF CHANGE ---
                
                if processed_at:
                    if detected_faces:
                        expander_title += f" ({len(detected_faces)} face(s) found)"
                    else:
                        expander_title += " (Processed, no faces found)"
                else:
                    expander_title += " (Not Processed)"

                with st.expander(expander_title):
                    image_b64 = event_data.pop("imageBaseString", None)
                    display_data = event_data.copy()
                    display_data.pop("processed_at", None)
                    display_data.pop("detected_faces", None)
                    
                    disp_col1, disp_col2 = st.columns([1, 2])

                    with disp_col2:
                        st.subheader("Event Image Analysis")
                        if image_b64:
                            try:
                                if image_b64.startswith("data:image"):
                                    image_b64 = image_b64.split(",", 1)[1]
                                img_data = base64.b64decode(image_b64)
                                img = Image.open(io.BytesIO(img_data))
                                
                                if detected_faces:
                                    img_with_boxes = draw_bounding_boxes(img, detected_faces)
                                    st.image(img_with_boxes, caption="Image with Face Analysis", use_container_width=True)
                                else:
                                    st.image(img, caption="Event Image", use_container_width=True)
                            except Exception as e:
                                st.error(f"Could not display image: {e}")
                        else:
                            st.info("No image available for this event.")
                    
                    with disp_col1:
                        st.subheader("Event Metadata")
                        st.json(display_data)
                        
                        st.subheader("Facial Recognition Results")
                        if processed_at:
                            if detected_faces:
                                for face_result in detected_faces:
                                    st.json(face_result)
                            else:
                                st.info("This event was processed, but no faces were found.")
                        else:
                            st.info("This event has not been processed for facial recognition yet.")

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching events from the backend: {e}")
    except json.JSONDecodeError:
        st.error("Failed to decode JSON from the response.")
        if 'response' in locals():
            st.code(f"Raw Response (first 500 chars):\n{response.text[:500]}", language=None)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")