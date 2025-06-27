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

    def to_pixel_box(self, image_width: int, image_height: int) -> tuple[int, int, int, int]:
        """
        Calculates the (left, top, right, bottom) pixel tuple for Pillow's crop method.

        This is the most direct and reliable way to convert the coordinates.
        - left = Left_ratio * image_width
        - top = Top_ratio * image_height
        - right = (Left_ratio + Width_ratio) * image_width
        - bottom = (Top_ratio + Height_ratio) * image_height
        """
        left_px = int(self.Left * image_width)
        top_px = int(self.Top * image_height)
        right_px = int((self.Left + self.Width) * image_width)
        bottom_px = int((self.Top + self.Height) * image_height)
        return (left_px, top_px, right_px, bottom_px)

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
