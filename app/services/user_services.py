from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from io import BytesIO
from PIL import Image
import httpx

from ..models.user_models import UserModel
from ..models.user_api_models import CreateUserRequest
# --- CHANGED: Import from the refactored user_operations.py ---
from ..crud.user_operations import create_user_in_db, get_user_by_face_id, get_all_users_from_db, get_user_by_id
from ..services import aws_services, event_services
from ..models.aws_models import BoundingBox
from ..core.logging import get_logger

logger = get_logger("user-services")

# --- CHANGED: Function is now synchronous and does not take a db parameter ---
def create_new_user(user_data: CreateUserRequest) -> dict:
    """
    Service function to create a new user.

    Args:
        user_data: The user creation request data.

    Returns:
        The created user document as a dictionary.
    """
    user_to_create = UserModel(**user_data.model_dump(by_alias=True))
    # --- CHANGED: Synchronous call without db parameter ---
    created_user_doc = create_user_in_db(user_to_create)
    return created_user_doc


def get_all_users_data() -> List[Dict[str, Any]]:
    """
    Service function to retrieve all users.
    """
    user_docs = get_all_users_from_db()
    return user_docs


def get_user_by_face_id_data(face_id: str) -> Optional[Dict[str, Any]]:
    """
    Service function to retrieve a user by one of their associated face IDs.

    Args:
        face_id: The Rekognition FaceId to search for.

    Returns:
        The user document as a dictionary if found, otherwise None.
    """
    user_doc = get_user_by_face_id(face_id)
    return user_doc


def get_rekognition_users_data(collection_id: str) -> List[Dict[str, Any]]:
    """
    Service function to retrieve all users from a Rekognition collection.
    """
    # The aws_services function already handles logging and exceptions.
    # The API layer will catch the exception if one is raised.
    return aws_services.list_users(collection_id)


def get_user_by_id_data(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Service function to retrieve a user by their ID.
    """
    user_doc = get_user_by_id(user_id)
    return user_doc


def get_cropped_face_image_bytes(face_id: str) -> Optional[bytes]:
    """
    Finds an event for a face, gets the image, and returns the bytes of the cropped face.
    """
    events = event_services.get_events_data(face_id=face_id)
    if not events:
        logger.warning(f"No event found for faceId {face_id}")
        return None

    target_event = next((event for event in events if event.get("s3ImageKey") and event.get("detected_faces")), None)
    if not target_event:
        logger.warning(f"No event with image/face data found for faceId {face_id}")
        return None

    s3_key = target_event.get("s3ImageKey")
    presigned_url = aws_services.create_presigned_url(s3_key)
    if not presigned_url:
        logger.error(f"Could not get presigned URL for s3_key {s3_key}")
        return None
    
    try:
        image_response = httpx.get(presigned_url, timeout=30)
        image_response.raise_for_status()
        img = Image.open(BytesIO(image_response.content))
        img_width, img_height = img.size
    except Exception as e:
        logger.error(f"Failed to download or open image from S3 for faceId {face_id}: {e}")
        return None

    target_face_details = None
    for face in target_event.get("detected_faces", []):
        face_info = face.get("face_info", {})
        if face_info and face_info.get("FaceId") == face_id:
            target_face_details = face.get("rekognition_details")
            break
    
    if not target_face_details or "BoundingBox" not in target_face_details:
        logger.warning(f"Could not find bounding box for faceId {face_id} in event.")
        return None

    bbox = target_face_details["BoundingBox"]
    left = int(bbox['Left'] * img_width)
    top = int(bbox['Top'] * img_height)
    right = int(left + (bbox['Width'] * img_width))
    bottom = int(top + (bbox['Height'] * img_height))
    
    cropped_img = img.crop((left, top, right, bottom))
    
    with BytesIO() as output:
        cropped_img.save(output, format=img.format or 'JPEG')
        return output.getvalue()

def compare_users_data(user_a_id: str, user_b_id: str) -> Dict[str, Any]:
    user_a = get_user_by_id_data(user_a_id)
    user_b = get_user_by_id_data(user_b_id)

    if not user_a or not user_a.get("faceIds"):
        raise HTTPException(status_code=404, detail=f"User A '{user_a_id}' not found or has no faces.")
    if not user_b or not user_b.get("faceIds"):
        raise HTTPException(status_code=404, detail=f"User B '{user_b_id}' not found or has no faces.")

    image_bytes_a = get_cropped_face_image_bytes(user_a["faceIds"][0])
    if not image_bytes_a:
        raise HTTPException(status_code=404, detail=f"Could not retrieve image for User A's face ({user_a['faceIds'][0]}).")
    
    image_bytes_b = get_cropped_face_image_bytes(user_b["faceIds"][0])
    if not image_bytes_b:
        raise HTTPException(status_code=404, detail=f"Could not retrieve image for User B's face ({user_b['faceIds'][0]}).")

    response, error = aws_services.compare_faces(image_bytes_a, image_bytes_b)
    if error:
        raise HTTPException(status_code=400, detail=f"AWS Rekognition error: {error}")
    
    if not response or not response.get("FaceMatches"):
        return {"similarity": 0.0, "sourceFaceMatch": False}

    match = response["FaceMatches"][0]
    return {"similarity": match.get("Similarity", 0.0), "sourceFaceMatch": True}