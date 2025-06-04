from pydantic import BaseModel
from typing import List
from datetime import datetime

class AppearanceEvent(BaseModel):
    objectId: int
    confidence: float
    generatorId: int
    cameraId: str
    eventStartTime: datetime
    eventEndTime: datetime
    eventTimestamp: datetime
    imageBaseString: str

class AppearanceRequest(BaseModel):
    total_length: int
    results: List[AppearanceEvent]
