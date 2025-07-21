# app/models/visualization_models.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

# This inner model represents the nested 'visualization' object.
class VisualizationDataModel(BaseModel):
    type: str
    format: str
    data: str

# This is the main model for the entire document in the 'visualizations' collection.
class VisualizationDocumentModel(BaseModel):
    id: str = Field(..., alias="_id")
    run_id: str
    model_type: Optional[str] = None
    created_at: datetime
    visualization: VisualizationDataModel

    class Config:
        # Allows Pydantic to create the model from object attributes (like from a DB record)
        from_attributes = True
        # Allows aliasing, so '_id' from MongoDB maps to 'id' in the model
        populate_by_name = True
        # Defines how to serialize complex types like ObjectId to JSON
        json_encoders = {
            ObjectId: str
        }