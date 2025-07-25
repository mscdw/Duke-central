from typing import Optional, Dict, Any
from ..models.user_models import UserModel
from ..models.user_api_models import CreateUserRequest
# --- CHANGED: Import from the refactored user_operations.py ---
from ..crud.user_operations import create_user_in_db, get_user_by_face_id


# --- CHANGED: Function is now synchronous and does not take a db parameter ---
def create_new_user(user_data: CreateUserRequest) -> dict:
    """
    Service function to create a new user.

    Args:
        user_data: The user creation request data.

    Returns:
        The created user document as a dictionary.
    """
    user_to_create = UserModel(**user_data.dict(by_alias=True))
    # --- CHANGED: Synchronous call without db parameter ---
    created_user_doc = create_user_in_db(user_to_create)
    return created_user_doc


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