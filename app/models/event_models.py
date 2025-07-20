from pydantic import BaseModel
from typing import List, Dict, Any


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