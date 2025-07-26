from pydantic import BaseModel, Field
from typing import List, Optional

class CreateUserRequest(BaseModel):
    """
    Request model for creating a new user.
    The '_id' must correspond to a valid and existing Rekognition UserId.
    """
    id: str = Field(..., alias="_id", description="The Rekognition UserId.")
    name: Optional[str] = Field(None, description="Application-specific name for the user (e.g., 'Jane Doe').")
    faceIds: List[str] = Field(..., min_length=1, description="A list of one or more Rekognition FaceIds to associate with the user.")

    class Config:
        """Pydantic configuration."""
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "user_jane_doe_12345",
                "name": "Jane Doe",
                "faceIds": ["d2e6c886-d456-46e6-b379-4d2cebcd45d0"]
            }
        }


# class CreateUserRequest(BaseModel):
#     id: str = Field(..., alias="_id")
#     name: Optional[str] = None
#     faceIds: List[str] = []


class CompareUsersRequest(BaseModel):
    userA_id: str
    userB_id: str


class MergeUsersRequest(BaseModel):
    """Request model for merging two users."""
    sourceUserId: str = Field(..., description="The ID of the user to merge from (will be deleted).")
    targetUserId: str = Field(..., description="The ID of the user to merge into.")

    class Config:
        schema_extra = {
            "example": {
                "sourceUserId": "user_to_delete_123",
                "targetUserId": "user_to_keep_456"
            }
        }