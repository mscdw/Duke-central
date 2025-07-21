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
    """
    Draws highly visible bounding boxes and labels for each detected face on the image.
    """
    # Create a copy to draw on
    img_with_boxes = image.convert("RGB")
    draw = ImageDraw.Draw(img_with_boxes)
    img_width, img_height = img_with_boxes.size

    # --- 1. DYNAMIC FONT SIZE ---
    # Calculate a font size that is proportional to the image height.
    # The 'max(15, ...)' ensures the font is at least 15pt.
    font_size = max(15, int(img_height / 40))
    try:
        # Try to load a common font. You may need to change 'arial.ttf'
        # to a font available on your system (e.g., 'sans-serif.ttf' on Linux).
        font = ImageFont.truetype("arial.ttf", size=font_size)
    except IOError:
        # Fallback to a default font if the specified one isn't found.
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

        # --- 2. THICKER BOUNDING BOX ---
        # Increased width for better visibility.
        draw.rectangle([left, top, right, bottom], outline=color, width=5)

        # --- 3. HIGH-CONTRAST TEXT BACKGROUND ---
        # Get the size of the text to be drawn
        text_bbox = draw.textbbox((left, top), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Draw a filled rectangle behind the text for readability.
        # Position it just above the main bounding box.
        text_bg_rect = [left, top - text_height - 10, left + text_width + 10, top]
        draw.rectangle(text_bg_rect, fill=color)

        # Draw the text on top of the background rectangle.
        # Use a contrasting color like white for the text itself.
        draw.text((left + 5, top - text_height - 5), label, font=font, fill="white")

    return img_with_boxes


# --- User Interface Area ---
st.subheader("1. Select Date Range")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", date.today() - timedelta(days=7))
with col2:
    end_date = st.date_input("End date", date.today())

st.subheader("2. Apply Filters (Optional)")

# --- NEW: Filter UI Elements ---
status_options = ["matched", "indexed", "low_quality_face", "error"]
col1, col2 = st.columns(2)
with col1:
    selected_statuses = st.multiselect("Filter by Face Status:", options=status_options)
    face_id_filter = st.text_input("Filter by specific Face ID:")
with col2:
    show_no_faces = st.checkbox("Show events processed with NO faces")
    show_unprocessed = st.checkbox("Show UNPROCESSED events")
    

# --- Main Logic ---
if st.button("Get Events", type="primary"):
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat() + "T23:59:59",
    }
    
    try:
        response = requests.get(f"{API_URL}/get-events", params=params)
        response.raise_for_status()
        events = response.json()

        # --- NEW: Filtering Logic ---
        if selected_statuses or face_id_filter or show_no_faces or show_unprocessed:
            filtered_events = []
            for event in events:
                is_match = False
                # Handle special checkbox filters first
                if show_unprocessed and not event.get('processed_at'):
                    filtered_events.append(event)
                    continue
                if show_no_faces and event.get('processed_at') and not event.get('detected_faces'):
                    filtered_events.append(event)
                    continue
                
                # Check against status and Face ID filters
                detected_faces = event.get('detected_faces', [])
                for face in detected_faces:
                    # Check status match
                    if selected_statuses and face.get('status') in selected_statuses:
                        is_match = True
                        break
                    # Check Face ID match
                    face_info = face.get('face_info')
                    if face_id_filter and face_info and face_info.get('FaceId') == face_id_filter:
                        is_match = True
                        break
                
                if is_match:
                    filtered_events.append(event)
            
            # If any primary filters were used, replace the event list with the filtered list
            if selected_statuses or face_id_filter:
                events = filtered_events

        if not events:
            st.warning("No events found for the selected date range and filters.")
        else:
            st.success(f"Found {len(events)} events.")
            
            for i, event_data in enumerate(events):
                processed_at = event_data.get('processed_at')
                detected_faces = event_data.get('detected_faces', [])
                
                expander_title = f"Event {i+1} - ID: {event_data.get('eventId', 'N/A')}"
                if processed_at:
                    if detected_faces:
                        expander_title += f" ({len(detected_faces)} face(s) found)"
                    else:
                        expander_title += " (Processed, no faces found)"
                else:
                    expander_title += " (Not Processed)"

                with st.expander(expander_title):
                    # ... (The display logic from here is the same as the last version) ...
                    image_b64 = event_data.pop("imageBaseString", None)
                    event_data.pop("processed_at", None)
                    event_data.pop("detected_faces", None)
                    
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
                        st.json(event_data)
                        
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
