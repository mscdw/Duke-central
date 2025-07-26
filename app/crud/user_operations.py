from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status
from typing import Optional, Dict, Any, List

# --- ADDED: Import the db instance directly, following the event_operations pattern ---
from app.db.mongodb import db
from ..models.user_models import UserModel
from app.core.logging import get_logger

logger = get_logger("user-crud")

# --- CHANGED: Function is now synchronous and no longer requires a db instance to be passed in ---
def create_user_in_db(user: UserModel):
    """
    Inserts a new user document into the 'users' collection.
    This version is synchronous and uses the global db instance.

    Args:
        user: The UserModel object to be inserted.

    Returns:
        The dictionary representation of the inserted user.

    Raises:
        HTTPException: If a user with the same _id already exists (409 Conflict).
    """
    user_doc = user.model_dump(by_alias=True)
    try:
        # --- CHANGED: Use the imported db object for a synchronous call ---
        db["users"].insert_one(user_doc)
        return user_doc
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with ID '{user.id}' already exists.",
        )


def get_all_users_from_db() -> List[Dict[str, Any]]:
    """
    Retrieves all user documents from the 'users' collection, sorted by creation date.

    Returns:
        A list of user documents.
    """
    return list(db["users"].find({}).sort("createdAt", -1))



def get_user_by_face_id(face_id: str) -> Optional[Dict[str, Any]]:
    """
    Finds a user document by searching for a faceId within the 'faceIds' array.

    Args:
        face_id: The Rekognition FaceId to search for.

    Returns:
        The user document as a dictionary if found, otherwise None.
    """
    # Query to find a document where the 'faceIds' array contains the given face_id
    return db["users"].find_one({"faceIds": face_id})


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single user document from the 'users' collection by its _id.
    """
    logger.info(f"Querying for user with _id: {user_id}")
    user_doc = db["users"].find_one({"_id": user_id})
    if user_doc:
        logger.info(f"Found user document for _id: {user_id}")
    return user_doc


def add_faces_to_user_in_db(user_id: str, face_ids: List[str]) -> int:
    """
    Adds a list of face IDs to a user's 'faceIds' array in the database.
    Ensures that no duplicate face IDs are added.

    Args:
        user_id: The _id of the user to update.
        face_ids: A list of face IDs to add.

    Returns:
        The number of documents modified.
    """
    logger.info(f"Adding {len(face_ids)} faces to user '{user_id}' in DB.")
    result = db["users"].update_one(
        {"_id": user_id},
        {"$addToSet": {"faceIds": {"$each": face_ids}}}
    )
    logger.info(f"DB update result for adding faces to user '{user_id}': modified_count={result.modified_count}")
    return result.modified_count


def delete_user_from_db(user_id: str) -> int:
    """
    Deletes a user document from the 'users' collection by its _id.
    """
    logger.info(f"Deleting user '{user_id}' from DB.")
    result = db["users"].delete_one({"_id": user_id})
    logger.info(f"DB delete result for user '{user_id}': deleted_count={result.deleted_count}")
    return result.deleted_count