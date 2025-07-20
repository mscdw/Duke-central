import json
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import Response, JSONResponse
from app.core.logging import get_logger
from app.models.event_models import EventRequest, EventMediaUpdateRequest
from app.services.event_services import get_events_data, store_events_data, get_events_for_enrichment_data, update_events_with_media

router = APIRouter()
logger = get_logger("event-endpoints")

@router.post("/store-events", response_class=Response)
def store_events(request: EventRequest):
    """
    Receives a list of events and delegates them to the event service for storage.
    """
    logger.info(f"Received request to store {len(request.events)} events.")
    resp = store_events_data(request)
    if resp:
        return Response(content=json.dumps(resp), status_code=200, media_type="application/json")
    else:
        # Following the pattern of returning an empty JSON object on service failure
        return Response(content="{}", status_code=503, media_type="application/json")


@router.get("/events-for-enrichment", response_class=JSONResponse)
def get_events_for_enrichment(
    type: str,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Gets events that need their media field populated.
    This is used by the media enrichment scheduler.
    """
    logger.info(f"Request received for events to enrich. Type: {type}, Limit: {limit}")
    result = get_events_for_enrichment_data(event_type=type, limit=limit)
    return JSONResponse(content=result, status_code=200)


@router.post("/events/media", response_class=JSONResponse)
def update_events_media(request: EventMediaUpdateRequest):
    """
    Updates a batch of events with their media data (e.g., base64 image string).
    This is used by the media enrichment scheduler.
    """
    logger.info(f"Received request to update media for {len(request.updates)} events.")
    resp = update_events_with_media(request)
    if resp:
        return JSONResponse(content=resp, status_code=200)
    else:
        # Following the pattern of returning an empty JSON object on service failure
        return JSONResponse(content={}, status_code=503)


@router.get("/get-events", response_class=JSONResponse)
def get_events(
    start_date: str = Query(None, description="Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(None, description="End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
):
    """
    Gets events within a specified date range.
    """
    logger.info(f"Request received for events. Start: {start_date}, End: {end_date}")
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    result = get_events_data(start_date=start_dt, end_date=end_dt)
    return JSONResponse(content=result if result is not None else [], status_code=200)