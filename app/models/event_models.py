from pydantic import BaseModel, model_validator
from typing import List, Dict, Any, Optional, Literal
from app.models.appearance_models import FaceInfo

# --- NO CHANGES TO THESE MODELS ---

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

class EventResponse(BaseModel):
    """
    Defines the data structure for a single event returned by the API.
    """
    eventId: str
    title: str
    start: str
    end: str
    allDay: bool
    is_all_day: bool
    imageBaseString: Optional[str] = None
    class Config:
        schema_extra = { "example": {"eventId": "...", "title": "...", "start": "...", "end": "...", "allDay": False, "is_all_day": False, "imageBaseString": "..."} }


# --- MODIFICATIONS START HERE ---

class FaceProcessingInfo(BaseModel):
    """
    Detailed information about the outcome of the facial recognition processing attempt.
    """
    processed: bool
    processed_at: str  # ISO 8601 timestamp string
    match_result: Literal["matched", "indexed", "no_face", "error"]
    new_face_indexed: bool
    error_message: Optional[str] = None


class EventFacialRecognitionUpdate(BaseModel):
    """
    Defines the structure for a single event facial recognition update.
    This now includes detailed processing status.
    """
    eventId: str
    # personId and personFace are now optional, as they only exist for "matched" or "indexed" statuses.
    personId: Optional[str] = None
    personFace: Optional[FaceInfo] = None
    # This new field contains the detailed processing outcome.
    face_processing: FaceProcessingInfo


class EventFacialRecognitionUpdateRequest(BaseModel):
    """
    Defines the request body for updating events with facial recognition data.
    The example is updated to reflect the new, more detailed payload.
    """
    updates: List[EventFacialRecognitionUpdate]

    class Config:
        schema_extra = {
            "example": {
                "updates": [
                    {
                        "eventId": "event-id-matched",
                        "personId": "rekognition-face-id-123",
                        "personFace": {
                            "FaceId": "rekognition-face-id-123",
                            "BoundingBox": {"Width": 0.1, "Height": 0.2, "Left": 0.3, "Top": 0.4},
                            "ImageId": "source-image-id",
                            "Confidence": 99.9
                        },
                        "face_processing": {
                            "processed": True,
                            "processed_at": "2023-10-27T10:00:00Z",
                            "match_result": "matched",
                            "new_face_indexed": False
                        }
                    },
                    {
                        "eventId": "event-id-no-face",
                        "personId": None,
                        "personFace": None,
                        "face_processing": {
                            "processed": True,
                            "processed_at": "2023-10-27T10:01:00Z",
                            "match_result": "no_face",
                            "new_face_indexed": False
                        }
                    },
                     {
                        "eventId": "event-id-error",
                        "personId": None,
                        "personFace": None,
                        "face_processing": {
                            "processed": True,
                            "processed_at": "2023-10-27T10:02:00Z",
                            "match_result": "error",
                            "new_face_indexed": False,
                            "error_message": "Rekognition API call failed."
                        }
                    }
                ]
            }
        }
# --- MODIFICATIONS END HERE ---