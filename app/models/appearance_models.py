from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ROI(BaseModel):
    left: float
    top: float
    right: float
    bottom: float

class AppearanceEvent(BaseModel):
    objectId: int
    confidence: float
    generatorId: int
    cameraId: str
    eventStartTime: datetime
    eventEndTime: datetime
    objectROI: Optional[ROI] = None
    objectTimeStamp: Optional[datetime] = None
    faceROI: Optional[ROI] = None
    faceTimeStamp: Optional[datetime] = None
    imageBaseString: str

class AppearanceRequest(BaseModel):
    total_length: int
    results: List[AppearanceEvent]
