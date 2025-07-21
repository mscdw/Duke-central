from pydantic import BaseModel, model_validator, Field
from typing import List, Dict, Any, Optional, Literal

# Import from 'appearance_models' which is in a different file, so this is OKAY.
from app.models.appearance_models import FaceInfo


# --- UNCHANGED MODELS ---
# These models are for other API endpoints and do not need to change.

class EventRequest(BaseModel):
    """
    Defines the expected request body for the /store-events endpoint.
    """
    events: List[Dict[str, Any]]
    class Config:
        schema_extra = { "example": { "events": [{"eventType": "user_login", "userId": "user123", "timestamp": "2023-10-27T10:00:00Z"}] } }

class EventMediaUpdate(BaseModel):
    """
    Defines the structure for a single event media update.
    Requires at least one of imageBaseString or json.
    """
    eventId: str
    imageBaseString: Optional[str] = None
    json: Optional[str] = None

    @model_validator(mode='after')
    def check_media_present(self) -> 'EventMediaUpdate':
        if self.imageBaseString is None and self.json is None:
            raise ValueError("At least one of 'imageBaseString' or 'json' must be provided.")
        return self

class EventMediaUpdateRequest(BaseModel):
    """Defines the request body for the /events/media endpoint."""
    updates: List[EventMediaUpdate]
    class Config:
        schema_extra = { "example": {"updates": [{"eventId": "some-event-id-1", "imageBaseString": "..."}]} }


# --- MODELS WITH CHANGES FOR MULTI-FACE PROCESSING ---

class EventResponse(BaseModel):
    """
    Defines the data structure for a single event returned by the API.
    Now includes facial recognition results.
    """
    eventId: str
    title: str
    start: str
    end: str
    allDay: bool
    is_all_day: bool
    imageBaseString: Optional[str] = None
    processed_at: Optional[str] = None
    
    # --- FIX 1: Use a string "forward reference" to avoid circular import ---
    detected_faces: Optional[List['FaceProcessingResult']] = None
    # --- END FIX 1 ---


class FaceProcessingResult(BaseModel):
    """
    Holds the complete processing result for a single detected face within an image.
    This structure will be part of a list within the main event update.
    """
    status: Literal["matched", "indexed", "low_quality_face", "error"] = Field(
        ...,
        description="The final processing status for this specific face."
    )
    
    face_info: Optional[FaceInfo] = Field(
        default=None,
        description="Biometric and reference info from search/index operations. Null if status is not 'matched' or 'indexed'."
    )
    
    rekognition_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The raw, detailed JSON object for this face from the AWS Rekognition DetectFaces API."
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="An error message if the status is 'error'."
    )
    

class EventFacialRecognitionUpdate(BaseModel):
    """
    Defines the structure for updating a single event with the results
    of processing ALL faces found in its associated image.
    """
    eventId: str = Field(..., description="The unique ID of the event being updated.")
    
    processed_at: str = Field(
        ..., 
        description="The ISO 8601 timestamp when the facial recognition process was completed."
    )
    
    # This is okay because FaceProcessingResult is defined above it in the file.
    detected_faces: List[FaceProcessingResult] = Field(
        ...,
        description="A list of processing results, one for each face found in the event's image."
    )


class EventFacialRecognitionUpdateRequest(BaseModel):
    """
    Defines the request body for the `/events/with-recognition` endpoint.
    It expects a list of event updates.
    """
    updates: List[EventFacialRecognitionUpdate]

    class Config:
        # A new, comprehensive example showing the multi-face structure.
        schema_extra = {
            "example": {
                "updates": [
                    {
                        "eventId": "event-with-two-faces",
                        "processed_at": "2023-10-28T12:00:00Z",
                        "detected_faces": [
                            {
                                "status": "matched",
                                "face_info": {
                                    "FaceId": "face-id-123",
                                    "BoundingBox": {"Width": 0.1, "Height": 0.2, "Left": 0.1, "Top": 0.1},
                                    "ImageId": "image-id-abc",
                                    "Confidence": 99.8
                                },
                                "rekognition_details": {
                                    "AgeRange": {"Low": 25, "High": 35},
                                    "Emotions": [{"Type": "HAPPY", "Confidence": 98.7}]
                                },
                                "error_message": None
                            },
                        ]
                    },
                ]
            }
        }

# --- FIX 2: Rebuild the model that used the forward reference ---
# This line must be at the end of the file, after all models are defined.
# It tells Pydantic to resolve the string 'FaceProcessingResult' in EventResponse
# into the actual FaceProcessingResult class.
EventResponse.model_rebuild()
# --- END FIX 2 ---