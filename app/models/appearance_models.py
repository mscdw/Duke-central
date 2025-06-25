from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ROI(BaseModel):
    left: float
    top: float
    right: float
    bottom: float

class BoundingBox(BaseModel):
    Width: float
    Height: float
    Left: float
    Top: float

class FaceInfo(BaseModel):
    FaceId: str
    BoundingBox: BoundingBox
    ImageId: str
    Confidence: float

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
    personId: Optional[str] = None
    personFace: Optional[FaceInfo] = None

class AppearanceRequest(BaseModel):
    total_length: int
    results: List[AppearanceEvent]
