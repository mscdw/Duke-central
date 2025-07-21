# app/routers/visualization_endpoints.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.core.logging import get_logger
from app.models.visualizations_models import VisualizationDocumentModel
# The service import is correct
from app.services.visualization_services import get_visualization_data_by_run_id

router = APIRouter()
logger = get_logger("visualization-endpoints")

@router.get(
    "/get-visualization",
    response_model=VisualizationDocumentModel,
    summary="Get a Visualization by Run ID",
    description="Fetches a single visualization document from the `visualizations` collection using its `run_id`."
)
# The function still should be async, which is correct for a FastAPI endpoint
async def get_visualization(
    run_id: str = Query(
        ..., 
        description="The run_id associated with the visualization to fetch."
    )
):
    """
    Endpoint to retrieve a specific visualization from the database.
    """
    logger.info(f"Request received for visualization with run_id: {run_id}")
    try:
        # --- FIXED: Removed the 'await' keyword ---
        # The service function is synchronous, so we call it directly.
        visualization_doc = get_visualization_data_by_run_id(run_id)
        
        if not visualization_doc:
            raise HTTPException(
                status_code=404, 
                detail=f"Visualization not found for run_id: {run_id}"
            )
            
        return visualization_doc
        
    except Exception as e:
        logger.error(f"An unhandled error occurred in /get-visualization endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")