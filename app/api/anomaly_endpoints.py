# routers/anomaly_endpoints.py

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.core.logging import get_logger
from app.models.anomaly_models import AnomalyReportModel
from app.services.anomaly_services import get_anomaly_reports_data

router = APIRouter()
logger = get_logger("anomaly-endpoints")

@router.get(
    "/get-anomaly-reports",
    response_model=List[AnomalyReportModel],
    summary="Get Anomaly Detection Reports",
    description="Fetches a list of anomaly reports, with optional filtering by date range and person ID."
)
def get_anomaly_reports(
    start_date: Optional[str] = Query(
        None, 
        description="Filter reports from this profile_date onwards (YYYY-MM-DD)",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Query(
        None, 
        description="Filter reports up to this profile_date (YYYY-MM-DD)",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    personId: Optional[str] = Query(
        None, 
        description="Filter reports for a specific personId"
    )
):
    """
    Endpoint to retrieve anomaly reports from the database.
    """
    logger.info(
        f"Request received for anomaly reports. "
        f"Filters: start_date={start_date}, end_date={end_date}, personId={personId}"
    )
    try:
        # The service function does the heavy lifting
        reports = get_anomaly_reports_data(
            start_date=start_date, 
            end_date=end_date, 
            personId=personId
        )
        # The 'response_model' will automatically validate the list of dicts
        # against List[AnomalyReportModel] and serialize it correctly.
        return reports
    except Exception as e:
        logger.error(f"An unhandled error occurred in /get-anomaly-reports endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")