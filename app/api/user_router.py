# --- CHANGED: Request is no longer needed for the database connection ---
from fastapi import APIRouter, status, Body, HTTPException
from botocore.exceptions import ClientError
from ..models.user_models import UserModel
from ..models.user_api_models import CreateUserRequest
from ..services.user_services import create_new_user, get_user_by_face_id_data, get_all_users_data, get_rekognition_users_data
from typing import List, Dict, Any

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get(
    "/",
    response_description="Get all users",
    response_model=List[UserModel],
)
def get_all_users_route():
    """
    Retrieves all user documents from the 'users' collection, sorted by most
    recently created.
    """
    users = get_all_users_data()
    return users

@router.post(
    "/",
    response_description="Create a new user",
    status_code=status.HTTP_201_CREATED,
    response_model=UserModel,
)
# --- CHANGED: The endpoint is now synchronous and no longer needs the request object ---
def create_user(user_data: CreateUserRequest = Body(...)):
    """
    Creates a new user document in the 'users' collection.

    This endpoint synchronizes the application's user database with AWS Rekognition.
    It should be called after a new user has been created in Rekognition.

    - **_id**: The unique Rekognition `UserId`.
    - **name**: An optional, human-readable name for the user.
    - **faceIds**: The initial list of Rekognition `FaceId`s associated with this user.
    """
    # The service function now handles the business logic, which in turn calls
    # the CRUD layer to interact with the database. The HTTPException for
    # duplicates is raised from the CRUD layer and will be handled by FastAPI.
    # --- CHANGED: The call is now synchronous and doesn't pass the db connection ---
    created_user = create_new_user(user_data)
    return created_user


@router.get(
    "/by-face-id/{face_id}",
    response_model=UserModel,
    response_description="Get a user by a Rekognition FaceId",
    summary="Find User by Face ID"
)
def get_user_by_face_id_route(face_id: str):
    """
    Retrieves a user document by searching for a specific `FaceId` associated with them.
    This is used to link a detected face back to a known user.
    """
    user = get_user_by_face_id_data(face_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with FaceId '{face_id}'"
        )
    return user


@router.get(
    "/from-rekognition/{collection_id}",
    response_model=List[Dict[str, Any]],
    response_description="Get all users directly from a Rekognition collection",
    summary="List Rekognition Users"
)
def get_rekognition_users_route(collection_id: str):
    """
    Retrieves all user records directly from the specified AWS Rekognition collection.
    This is useful for auditing and comparing against the central database.
    """
    try:
        users = get_rekognition_users_data(collection_id)
        return users
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error fetching users from Rekognition collection '{collection_id}': {e.response['Error']['Message']}"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
