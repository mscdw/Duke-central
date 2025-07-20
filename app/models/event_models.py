from pydantic import BaseModel, model_validator
from typing import List, Dict, Any, Optional


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