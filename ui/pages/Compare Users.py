import streamlit as st
import httpx
import os
from PIL import Image
import io

# --- Configuration ---
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL", "http://localhost:8001")

# --- Page Setup ---
st.set_page_config(page_title="Compare Users", layout="wide")
st.title("👯 User Similarity Comparison")
st.markdown("Select two users to compare their representative faces for a similarity score.")

# --- API Client Functions ---
@st.cache_data(ttl=60)
def get_all_users():
    """Fetches all users from the backend."""
    try:
        url = f"{CENTRAL_API_URL}/users/"
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch users: {e}")
        return []

@st.cache_data(ttl=3600)
def get_face_image_for_user(user_id: str):
    """Gets a representative face image for a user."""
    if not user_id:
        return None
    try:
        # Get user to find a faceId
        user_url = f"{CENTRAL_API_URL}/users/{user_id}"
        user_resp = httpx.get(user_url, timeout=10)
        user_resp.raise_for_status()
        user_data = user_resp.json()
        face_ids = user_data.get("faceIds")

        if not face_ids:
            return "No faces for user"

        face_id = face_ids[0]

        # Find an event for that faceId
        event_url = f"{CENTRAL_API_URL}/get-events?faceId={face_id}&limit=1"
        event_resp = httpx.get(event_url, timeout=15)
        event_resp.raise_for_status()
        events = event_resp.json()

        if not events:
            return "No event found for face"

        target_event = next((e for e in events if e.get("s3ImageKey") and e.get("detected_faces")), None)
        if not target_event:
            return "No event with image data"

        # Get image and crop it
        s3_key = target_event.get("s3ImageKey")
        presigned_url_req = f"{CENTRAL_API_URL}/get-presigned-url?s3Key={s3_key}"
        url_response = httpx.get(presigned_url_req, timeout=15)
        url_response.raise_for_status()
        presigned_url = url_response.json()

        image_response = httpx.get(presigned_url, timeout=30)
        image_response.raise_for_status()
        img = Image.open(io.BytesIO(image_response.content))
        img_width, img_height = img.size

        target_face_details = None
        for face in target_event.get("detected_faces", []):
            face_info = face.get("face_info", {})
            if face_info and face_info.get("FaceId") == face_id:
                target_face_details = face.get("rekognition_details")
                break
        
        if not target_face_details or "BoundingBox" not in target_face_details:
            return "Bounding box not found"

        bbox = target_face_details["BoundingBox"]
        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        right = int(left + (bbox['Width'] * img_width))
        bottom = int(top + (bbox['Height'] * img_height))
        
        return img.crop((left, top, right, bottom))

    except Exception as e:
        return f"Error: {e}"

# --- Main Page Logic ---
users = get_all_users()

if not users:
    st.warning("No users available for comparison.")
else:
    user_options = {f"{user.get('_id')} (Name: {user.get('name', 'N/A')})": user.get('_id') for user in users}
    user_display_list = [""] + list(user_options.keys())

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("User A")
        user_a_display = st.selectbox("Select User A", options=user_display_list, key="user_a", index=0)
        user_a_id = user_options.get(user_a_display)
        if user_a_id:
            st.write(f"**ID:** `{user_a_id}`")
            with st.spinner("Loading face for User A..."):
                img_a = get_face_image_for_user(user_a_id)
                if isinstance(img_a, Image.Image):
                    st.image(img_a, caption="Representative Face for User A", use_container_width=True)
                else:
                    st.warning(f"Could not load image: {img_a}")

    with col2:
        st.subheader("User B")
        user_b_display = st.selectbox("Select User B", options=user_display_list, key="user_b", index=0)
        user_b_id = user_options.get(user_b_display)
        if user_b_id:
            st.write(f"**ID:** `{user_b_id}`")
            with st.spinner("Loading face for User B..."):
                img_b = get_face_image_for_user(user_b_id)
                if isinstance(img_b, Image.Image):
                    st.image(img_b, caption="Representative Face for User B", use_container_width=True)
                else:
                    st.warning(f"Could not load image: {img_b}")

    st.divider()

    if st.button("🚀 Compare Users", disabled=not (user_a_id and user_b_id), use_container_width=True, type="primary"):
        if user_a_id == user_b_id:
            st.warning("Please select two different users to compare.")
        else:
            with st.spinner("Comparing faces..."):
                try:
                    compare_url = f"{CENTRAL_API_URL}/users/compare"
                    payload = {"userA_id": user_a_id, "userB_id": user_b_id}
                    response = httpx.post(compare_url, json=payload, timeout=60)
                    response.raise_for_status()
                    result = response.json()
                    
                    similarity = result.get("similarity", 0.0)
                    
                    st.subheader("Comparison Result")
                    if similarity > 90:
                        st.success(f"Similarity: **{similarity:.2f}%** - These are likely the same person.")
                    elif similarity > 70:
                        st.warning(f"Similarity: **{similarity:.2f}%** - These might be the same person.")
                    else:
                        st.error(f"Similarity: **{similarity:.2f}%** - These are likely different people.")

                except httpx.HTTPStatusError as e:
                    st.error(f"API Error: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")