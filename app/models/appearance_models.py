from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ROI(BaseModel):
    left: float
    top: float
    right: float
    bottom: float

class Snapshot(BaseModel):
    type: str
    timestamp: datetime
    roi: ROI
    description: Optional[str] = None

class AppearanceEvent(BaseModel):
    objectId: int
    confidence: float
    generatorId: int
    cameraId: str
    eventStartTime: datetime
    eventEndTime: datetime
    snapshots: List[Snapshot]
    siteName: str
    imageBaseString: str

class AppearanceRequest(BaseModel):
    total_length: int
    results: List[AppearanceEvent]
