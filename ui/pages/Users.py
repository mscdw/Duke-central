import streamlit as st
import httpx
from datetime import datetime
import os, sys
from PIL import Image, ImageDraw, ImageFont
import io


# --- Configuration ---
# Use an environment variable for the API URL, with a sensible default for local dev.
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL", "http://localhost:8001")

# --- Page Setup ---
st.set_page_config(page_title="User Dashboard", layout="wide")
st.title("👥 User Dashboard")
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

def update_user_name(user_id: str, new_name: str):
    """Updates a user's name via the API."""
    try:
        url = f"{CENTRAL_API_URL}/users/{user_id}"
        payload = {"name": new_name}
        response = httpx.patch(url, json=payload, timeout=15)
        response.raise_for_status()
        return True, "Name updated successfully!"
    except httpx.HTTPStatusError as e:
        error_message = f"API Error: {e.response.status_code} - {e.response.text}"
        st.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        st.error(error_message)
        return False, error_message

def merge_users_api(source_user_id: str, target_user_id: str):
    """Calls the backend to merge two users."""
    try:
        url = f"{CENTRAL_API_URL}/users/merge"
        payload = {"sourceUserId": source_user_id, "targetUserId": target_user_id}
        # Use a longer timeout for merge as it involves multiple backend operations
        response = httpx.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return True, "Users merged successfully!"
    except httpx.HTTPStatusError as e:
        error_message = f"API Error: {e.response.status_code} - {e.response.text}"
        st.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        st.error(error_message)
        return False, error_message

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cropped_face_image(face_id: str):
    """
    Finds the first event for a face, gets its image, and returns the cropped face.
    Returns a PIL Image object or None.
    """
    if not face_id:
        return None
    try:
        # 1. Find an event associated with the faceId, limit to 1 for efficiency
        event_url = f"{CENTRAL_API_URL}/get-events?faceId={face_id}&limit=1"
        event_response = httpx.get(event_url, timeout=15)
        event_response.raise_for_status()
        events = event_response.json()

        if not events:
            return None

        # Find the first event that has an image and face detection data
        target_event = next((e for e in events if e.get("s3ImageKey") and e.get("detected_faces")), None)

        if not target_event:
            return None

        # 2. Get a presigned URL for the S3 key
        s3_key = target_event.get("s3ImageKey")
        presigned_url_req = f"{CENTRAL_API_URL}/get-presigned-url?s3Key={s3_key}"
        url_response = httpx.get(presigned_url_req, timeout=15)
        url_response.raise_for_status()
        presigned_url = url_response.json()
        
        # 3. Download image
        image_response = httpx.get(presigned_url, timeout=30)
        image_response.raise_for_status()
        img = Image.open(io.BytesIO(image_response.content))
        img_width, img_height = img.size

        # 4. Find the specific face's bounding box
        target_face_details = None
        for face in target_event.get("detected_faces", []):
            # The faceId in the detected_faces list should match our target face_id
            if face.get("faceId") == face_id:
                target_face_details = face.get("rekognition_details")
                break
        
        if not target_face_details or "BoundingBox" not in target_face_details:
            return None

        # 5. Crop the image
        bbox = target_face_details["BoundingBox"]
        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        right = int(left + (bbox['Width'] * img_width))
        bottom = int(top + (bbox['Height'] * img_height))
        
        return img.crop((left, top, right, bottom))

    except Exception as e:
        # Don't show error in UI, just log it.
        print(f"Error getting cropped image for {face_id}: {e}")
        return None

def create_face_collage(face_ids: list, max_faces: int = 5) -> Image.Image | None:
    """
    Creates a horizontal collage from a list of face IDs.
    """
    if not face_ids:
        return None

    face_images = []
    for face_id in face_ids[:max_faces]:
        img = get_cropped_face_image(face_id)
        if img:
            face_images.append(img)

    if not face_images:
        return None

    # Standardize size (e.g., 100x100) and create collage
    face_size = (100, 100)
    resized_images = [img.resize(face_size) for img in face_images]

    total_width = sum(img.width for img in resized_images)
    max_height = max(img.height for img in resized_images)

    collage = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for img in resized_images:
        collage.paste(img, (x_offset, 0))
        x_offset += img.width

    return collage

def draw_bounding_boxes(image: Image.Image, faces: list, target_face_id: str) -> Image.Image:
    """Draws bounding boxes on an image, highlighting the target face."""
    img_with_boxes = image.convert("RGB")
    draw = ImageDraw.Draw(img_with_boxes)
    img_width, img_height = img_with_boxes.size

    font_size = max(15, int(img_height / 40))
    try:
        # Use a common font that's likely to be on the system
        font = ImageFont.truetype("DejaVuSans.ttf", size=font_size)
    except IOError:
        font = ImageFont.load_default()

    for face in faces:
        details = face.get("rekognition_details")
        if not details or "BoundingBox" not in details:
            continue

        bbox = details["BoundingBox"]
        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        right = int(left + (bbox['Width'] * img_width))
        bottom = int(top + (bbox['Height'] * img_height))

        current_face_id = face.get("faceId")
        
        if current_face_id == target_face_id:
            color = "#FF4B4B"  # Streamlit Red for highlight
            label = f"TARGET: {current_face_id[:8]}..."
            width = 7
        else:
            color = "#1E90FF"  # DodgerBlue for other faces
            label = f"Face: {current_face_id[:8]}..." if current_face_id else "Other Face"
            width = 3

        draw.rectangle([left, top, right, bottom], outline=color, width=width)
        
        text_bbox = draw.textbbox((left, top), label, font=font)
        text_height = text_bbox[3] - text_bbox[1]
        
        text_bg_rect = [left, top - text_height - 10, left + text_bbox[2] + 10, top]
        draw.rectangle(text_bg_rect, fill=color)
        draw.text((left + 5, top - text_height - 5), label, font=font, fill="white")

    return img_with_boxes

@st.cache_data(ttl=3600)
def get_annotated_and_cropped_image(face_id: str):
    """
    Finds the source event for a face, gets its image, and returns both a
    cropped version of the face and the full image with a bounding box.
    """
    if not face_id: return None
    try:
        event_url = f"{CENTRAL_API_URL}/get-events?faceId={face_id}&limit=1"
        event_response = httpx.get(event_url, timeout=15)
        event_response.raise_for_status()
        events = event_response.json()

        if not events: return {"error": "No event found for this FaceId."}
        target_event = next((e for e in events if e.get("s3ImageKey") and e.get("detected_faces")), None)
        if not target_event: return {"error": "No event with image/face data found."}

        s3_key = target_event.get("s3ImageKey")
        presigned_url_req = f"{CENTRAL_API_URL}/get-presigned-url?s3Key={s3_key}"
        url_response = httpx.get(presigned_url_req, timeout=15)
        url_response.raise_for_status()
        presigned_url = url_response.json()
        
        image_response = httpx.get(presigned_url, timeout=30)
        image_response.raise_for_status()
        img = Image.open(io.BytesIO(image_response.content))
        img_width, img_height = img.size

        detected_faces = target_event.get("detected_faces", [])
        target_face_details = next((f.get("rekognition_details") for f in detected_faces if f.get("faceId") == face_id), None)
        if not target_face_details or "BoundingBox" not in target_face_details: return {"error": "Bounding box not found."}

        bbox = target_face_details["BoundingBox"]
        left, top = int(bbox['Left'] * img_width), int(bbox['Top'] * img_height)
        right, bottom = int(left + (bbox['Width'] * img_width)), int(top + (bbox['Height'] * img_height))
        
        return {
            "cropped": img.crop((left, top, right, bottom)),
            "annotated": draw_bounding_boxes(img, detected_faces, face_id),
            "event": target_event
        }
    except Exception as e:
        return {"error": str(e)}

def render_user_list_view(users):
    """Renders the main dashboard of all users."""
    # --- Search and Sort Controls ---
    st.header("Filters & Sorting")
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input(
            "Search by User ID or Name",
            placeholder="Enter a user ID or name to filter..."
        ).lower()
    with col2:
        sort_key = st.selectbox(
            "Sort by",
            options=["createdAt", "faceCount", "_id", "name"],
            format_func=lambda x: {"createdAt": "Creation Date", "faceCount": "Face Count", "_id": "User ID", "name": "Name"}[x]
        )
        sort_ascending = st.toggle("Ascending", value=False if sort_key == "createdAt" else True)

    # --- Filtering Logic ---
    if search_term:
        filtered_users = [
            user for user in users
            if search_term in user.get('_id', '').lower() or \
               search_term in user.get('name', 'N/A').lower()
        ]
    else:
        filtered_users = users

    # --- Sorting Logic ---
    for user in filtered_users:
        user['faceCount'] = len(user.get('faceIds', []))

    filtered_users.sort(
        key=lambda u: u.get(sort_key) or (0 if sort_key == 'faceCount' else ''),
        reverse=not sort_ascending
    )

    st.divider()
    st.info(f"Displaying **{len(filtered_users)}** of **{len(users)}** total users.")

    # --- User List Display ---
    for user in filtered_users:
        user_id = user.get('_id')
        name = user.get('name', 'N/A')
        face_ids = user.get('faceIds', [])
        face_count = user.get('faceCount', 0)

        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader(name if name != 'N/A' else f"User {user_id[:8]}...")
                st.markdown(f"**ID:** `{user_id}`")
                st.markdown(f"**Faces Indexed:** {face_count}")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.button(
                        "View Details",
                        key=f"details_{user_id}",
                        on_click=lambda uid=user_id: st.session_state.update(selected_user_id=uid, source_user_for_merge=None),
                        use_container_width=True
                    )
                with btn_col2:
                    st.button(
                        "Merge...",
                        key=f"merge_{user_id}",
                        on_click=lambda u=user: st.session_state.update(source_user_for_merge=u, selected_user_id=None),
                        use_container_width=True,
                        type="secondary"
                    )

            with col2:
                if face_ids:
                    collage_image = create_face_collage(face_ids, max_faces=5)
                    if collage_image:
                        st.image(collage_image, caption="Representative faces")
                    else:
                        st.caption("Could not generate face collage.")
                else:
                    st.caption("No faces to display.")

def render_user_details_view(user_data):
    """Renders the detailed view for a single user."""
    user_id = user_data.get('_id')
    current_name = user_data.get('name', '')
    face_ids = user_data.get('faceIds', [])

    if st.button("⬅️ Back to User List"):
        st.session_state.selected_user_id = None
        st.rerun()

    st.header(f"Manage User: {current_name or user_id}")
    st.markdown(f"**User ID:** `{user_id}`")

    with st.form(key="update_name_form"):
        new_name = st.text_input("User Name", value=current_name, placeholder="e.g., Jane Doe")
        submitted = st.form_submit_button("Save Name")
        if submitted and new_name != current_name:
            success, message = update_user_name(user_id, new_name)
            if success:
                st.success(message)
                get_all_users.clear()
                st.rerun()

    st.divider()
    st.subheader(f"🖼️ Face Gallery ({len(face_ids)} faces)")
    if not face_ids:
        st.info("This user has no associated faces.")
        return

    cols = st.columns(3)
    for i, face_id in enumerate(face_ids):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**Face ID:**")
                st.code(face_id, language=None)
                with st.spinner(f"Loading face {face_id[:8]}..."):
                    image_data = get_annotated_and_cropped_image(face_id)
                
                if image_data and "error" not in image_data:
                    st.image(image_data["cropped"], caption="Cropped Face", use_container_width=True)
                    with st.expander("View Source Image & Event"):
                        st.image(image_data["annotated"], caption="Source Image with Bounding Box")
                        st.json(image_data["event"])
                else:
                    error_msg = image_data.get("error", "Unknown error") if image_data else "Failed to load"
                    st.error(f"Could not load image: {error_msg}")

def render_merge_view(source_user, all_users):
    """Renders the UI for merging two users."""
    st.header(f"Merge User: {source_user.get('name', source_user.get('_id'))}")

    if st.button("⬅️ Cancel Merge and Go Back"):
        st.session_state.source_user_for_merge = None
        st.rerun()

    st.warning("""
    **ACTION: MERGE USERS**

    You are about to move all faces from the **Source User** to the **Target User**.
    The Source User will be **permanently deleted**. This action cannot be undone.
    """, icon="⚠️")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Source User (will be deleted)")
        with st.container(border=True):
            st.markdown(f"**Name:** {source_user.get('name', 'N/A')}")
            st.markdown(f"**ID:** `{source_user.get('_id')}`")
            st.markdown(f"**Faces to move:** {source_user.get('faceCount', 0)}")
            collage = create_face_collage(source_user.get('faceIds', []))
            if collage:
                st.image(collage, caption="Source Faces")

    with col2:
        st.subheader("Target User (will receive faces)")

        # Create options for target user selection, excluding the source user
        target_user_options = {
            f"{u.get('name', 'N/A')} ({u.get('_id')})": u
            for u in all_users if u.get('_id') != source_user.get('_id')
        }

        selected_target_key = st.selectbox(
            "Search for and select the target user",
            options=[""] + list(target_user_options.keys()),
            index=0,
            help="Select the user profile you want to keep."
        )

        if selected_target_key:
            target_user = target_user_options[selected_target_key]
            with st.container(border=True):
                st.markdown(f"**Name:** {target_user.get('name', 'N/A')}")
                st.markdown(f"**ID:** `{target_user.get('_id')}`")
                st.markdown(f"**Current Faces:** {target_user.get('faceCount', 0)}")
                collage = create_face_collage(target_user.get('faceIds', []))
                if collage:
                    st.image(collage, caption="Target Faces")

            st.divider()

            if st.button("✅ Confirm Merge", type="primary", use_container_width=True):
                with st.spinner("Merging users... This may take a moment."):
                    success, message = merge_users_api(source_user.get('_id'), target_user.get('_id'))
                    if success:
                        st.success(message)
                        # Clear state and caches
                        st.session_state.source_user_for_merge = None
                        get_all_users.clear()
                        get_cropped_face_image.clear()
                        get_annotated_and_cropped_image.clear()
                        st.balloons()
                        st.rerun()

# --- Main Logic & View Routing ---

if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None
if "source_user_for_merge" not in st.session_state:
    st.session_state.source_user_for_merge = None

all_users = get_all_users()

if st.session_state.source_user_for_merge:
    render_merge_view(st.session_state.source_user_for_merge, all_users)
elif st.session_state.selected_user_id:
    selected_user = next((u for u in all_users if u.get('_id') == st.session_state.selected_user_id), None)
    if selected_user:
        render_user_details_view(selected_user)
    else:
        st.error(f"User with ID {st.session_state.selected_user_id} not found. Returning to list.")
        st.session_state.selected_user_id = None
        if st.button("Back to User List"): st.rerun()
else:
    if not all_users:
        st.warning("No users found in the database. The system may not have indexed any new faces yet.")
    else:
        render_user_list_view(all_users)
