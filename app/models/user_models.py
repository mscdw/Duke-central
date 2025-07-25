from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class UserModel(BaseModel):
    """
    Represents a user in the 'users' collection. This collection is the
    definitive source for each unique person recognized by the system, and is a
    direct counterpart to the User store within Rekognition.
    """
    id: str = Field(..., alias="_id", description="The Rekognition UserId, serving as the unique identifier.")
    name: Optional[str] = Field(None, description="Application-specific name for the user (e.g., 'Jane Doe').")
    faceIds: List[str] = Field(..., description="A list of all Rekognition FaceIds associated with this user.")
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp of when the user was first created.")
    updatedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp of when the user was last updated.")

    class Config:
        """Pydantic configuration."""
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "user_jane_doe_12345",
                "name": "Jane Doe",
                "faceIds": [
                    "d2e6c886-d456-46e6-b379-4d2cebcd45d0",
                    "f1c9a7b3-1234-5678-b1c2-abcdef123456"
                ],
                "createdAt": "2025-07-26T10:00:00Z",
                "updatedAt": "2025-07-28T14:30:00Z"
            }
        }