from pydantic import BaseModel

class BoundingBox(BaseModel):
    """
    A Pydantic model representing the bounding box of a detected face,
    as returned by AWS Rekognition.
    """
    Width: float
    Height: float
    Left: float
    Top: float