import logging
import json
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import  Response
from app.models.appearance_models import AppearanceRequest, AppearanceEvent
from app.services.appearance_services import store_appearances_data, get_appearances_data

router = APIRouter()
logger = logging.getLogger("appearance-endpoints")

@router.post("/store-appearances", response_class=Response)
def store_appearances(request: AppearanceRequest):
    resp = store_appearances_data(request)
    if resp:
        return Response(content=json.dumps(resp), status_code=200, media_type="application/json")
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/get-appearances", response_model=list[AppearanceEvent])
def get_appearances(
    start_date: str = Query(None, description="Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(None, description="End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
):
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    print(f"Fetching appearances from {start_dt} to {end_dt}")
    appearances = get_appearances_data(start_dt, end_dt)
    if appearances:
        return [AppearanceEvent(**a) for a in appearances]
    else:
        return []
