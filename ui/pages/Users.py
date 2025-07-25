import streamlit as st
import httpx
from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
import io

# st.cache_data.clear()


# --- Configuration ---
# Use an environment variable for the API URL, with a sensible default for local dev.
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL", "http://localhost:8001")

# --- Page Setup ---
st.set_page_config(page_title="User & Face Explorer", layout="wide")
st.title("👥 User & Face Explorer")
st.markdown("Browse all users recognized by the system and view their associated faces.")

# --- API Client Functions with Caching ---

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_all_users():
    """Fetches all users from the backend."""
    try:
        url = f"{CENTRAL_API_URL}/users/"
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        st.error(f"Failed to fetch users. Status code: {e.response.status_code}. Body: {e.response.text}")
    except Exception as e:
        st.error(f"An error occurred while fetching users: {e}")
    return []

def draw_bounding_boxes(image: Image.Image, faces: list) -> Image.Image:
    """Draws bounding boxes on an image for a list of faces."""
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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_annotated_face_image(face_id: str):
    """Finds the first event for a face, gets its image, and draws bounding boxes."""
    try:
        # 1. Find an event associated with the faceId
        event_url = f"{CENTRAL_API_URL}/get-events?faceId={face_id}"
        event_response = httpx.get(event_url, timeout=15)
        event_response.raise_for_status()
        events = event_response.json()

        if not events:
            return None, "No event found"

        # Find the first event that has an image and face detection data
        target_event = next((event for event in events if event.get("s3ImageKey") and event.get("detected_faces")), None)

        if not target_event:
            return None, "No event with image/face data"

        s3_key = target_event.get("s3ImageKey")
        detected_faces = target_event.get("detected_faces", [])
        
        # 2. Get a presigned URL for the S3 key
        presigned_url_req = f"{CENTRAL_API_URL}/get-presigned-url?s3Key={s3_key}"
        url_response = httpx.get(presigned_url_req, timeout=15)
        url_response.raise_for_status()
        presigned_url = url_response.json()
        
        # 3. Download and process image
        image_response = httpx.get(presigned_url, timeout=30)
        image_response.raise_for_status()
        img = Image.open(io.BytesIO(image_response.content))
        
        # 4. Draw boxes
        img_with_boxes = draw_bounding_boxes(img, detected_faces)
        return img_with_boxes, "Success"
    except Exception as e:
        print(f"Error getting annotated image for {face_id}: {e}")
        return None, "Error processing image"

# --- Main Page Logic ---

users = get_all_users()

if not users:
    st.warning("No users found in the database. The system may not have indexed any new faces yet.")
else:
    st.info(f"Found **{len(users)}** unique users, sorted by most recently created.")

    for user in users:
        user_id = user.get('_id')
        name = user.get('name', 'N/A')
        created_at_str = user.get('createdAt', '')
        try:
            # Handle timezone-aware and naive datetime strings
            created_at_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            created_at_display = created_at_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, TypeError):
            created_at_display = created_at_str

        with st.expander(f"**User ID:** `{user_id}` (Name: {name}) - Created: {created_at_display}"):
            st.write("#### Associated Faces")
            
            face_ids = user.get('faceIds', [])
            if not face_ids:
                st.write("No faces associated with this user.")
                continue

            # Display faces in columns for a clean layout
            cols = st.columns(4)
            for i, face_id in enumerate(face_ids):
                with cols[i % 4]:
                    st.markdown(f"**Face ID:**")
                    st.code(face_id, language=None)
                    annotated_image, status = get_annotated_face_image(face_id)
                    if annotated_image:
                        st.image(annotated_image, caption="Example sighting with analysis", use_container_width=True)
                    else:
                        st.caption(f"🖼️ No image available ({status})")
