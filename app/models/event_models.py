from pydantic import BaseModel, model_validator
from typing import List, Dict, Any, Optional
from app.models.appearance_models import FaceInfo


class EventRequest(BaseModel):
    """
    Defines the expected request body for the /store-events endpoint.
    """
    events: List[Dict[str, Any]]

    class Config:
        schema_extra = {
            "example": {
                "events": [
                    {"eventType": "user_login", "userId": "user123", "timestamp": "2023-10-27T10:00:00Z"},
                    {"eventType": "page_view", "path": "/home", "userId": "user456"}
                ]
            }
        }


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
        """Ensures at least one media type is provided."""
        if self.imageBaseString is None and self.json is None:
            raise ValueError(
                "At least one of 'imageBaseString' or 'json' must be provided for an event update."
            )
        return self


class EventMediaUpdateRequest(BaseModel):
    """Defines the request body for the /events/media endpoint."""
    updates: List[EventMediaUpdate]

    class Config:
        schema_extra = {
            "example": {
                "updates": [
                    {"eventId": "some-event-id-1", "imageBaseString": "base64-encoded-string-1"},
                    {"eventId": "some-event-id-2", "json": "{'data': 'some-json-data'}"},
                    {"eventId": "some-event-id-3", "imageBaseString": "...", "json": "{'data': '...'}"}
                ]
            }
        }

class EventResponse(BaseModel):
    """
    Defines the data structure for a single event returned by the API.
    """
    eventId: str
    title: str
    start: str  # The function returns a formatted string
    end: str    # The function returns a formatted string
    allDay: bool
    is_all_day: bool
    
    # --- THIS IS THE FIX ---
    # Add the missing image field.
    # It must be Optional because some events may not have an image.
    imageBaseString: Optional[str] = None

    class Config:
        # Example for OpenAPI/Swagger documentation
        schema_extra = {
            "example": {
                "eventId": "60c72b2f9b1e8a3f9e8b4567",
                "title": "DEVICE_CLASSIFIED_OBJECT_MOTION_START",
                "start": "2023-10-27T10:00:00",
                "end": "2023-10-27T11:00:00",
                "allDay": False,
                "is_all_day": False,
                # Also update the example to be more helpful
                "imageBaseString": "/9j/4AAQSkZJRgABAQEAYABgAAD...(etc)"
            }
        }


class EventFacialRecognitionUpdate(BaseModel):
    """
    Defines the structure for a single event facial recognition update.
    """
    eventId: str
    personId: str
    personFace: FaceInfo


class EventFacialRecognitionUpdateRequest(BaseModel):
    """Defines the request body for updating events with facial recognition data."""
    updates: List[EventFacialRecognitionUpdate]

    class Config:
        schema_extra = {
            "example": {
                "updates": [
                    {"eventId": "some-event-id-1", "personId": "some-person-id", "personFace": {"FaceId": "...", "BoundingBox": {"Width": 0.1, "Height": 0.2, "Left": 0.3, "Top": 0.4}, "ImageId": "...", "Confidence": 99.9}}
                ]
            }
        }