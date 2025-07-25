import json
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response, JSONResponse
from typing import Dict, Any, List, Optional 
from app.core.logging import get_logger
from app.models.event_models import EventRequest, EventMediaUpdateRequest, EventFacialRecognitionUpdateRequest
# --- 1. IMPORT THE NEW SERVICE FUNCTION ---
from app.services.event_services import (
    get_events_data,
    store_events_data,
    get_events_for_enrichment_data,
    get_presigned_url_for_s3_key,
    update_events_with_media,
    get_events_for_facial_recognition_data,
    update_events_with_facial_recognition_data,
    get_latest_event_timestamp_data # <-- Add this import
)

router = APIRouter()
logger = get_logger("event-endpoints")

# --- NO CHANGES TO ANY OF THE EXISTING FUNCTIONS ---

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
        return JSONResponse(content={}, status_code=503)


@router.get("/get-events", response_class=JSONResponse)
def get_events(
    start_date: str = Query(None, description="Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(None, description="End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    types: Optional[List[str]] = Query(None, alias="type", description="Filter by one or more event types."),
    camera_id: Optional[str] = Query(None, alias="cameraId", description="Filter events by a specific Camera ID."),
    # --- START OF CHANGE ---
    face_id: Optional[str] = Query(None, alias="faceId", description="Filter events by a specific Rekognition Face ID.")
    # --- END OF CHANGE ---
):
    """
    Gets events within a date range, optionally filtered by type, camera, and a specific Face ID.
    """
    logger.info(f"Request received for events. Start: {start_date}, End: {end_date}, Types: {types}, CameraID: {camera_id}, FaceID: {face_id}")
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    # Pass the new 'face_id' parameter down to the service layer function
    result = get_events_data(
        start_date=start_dt, 
        end_date=end_dt, 
        types=types, 
        face_id=face_id,
        camera_id=camera_id
    )
    
    return JSONResponse(content=result if result is not None else [], status_code=200)

# --- 2. ADD THE NEW API ROUTE ---
@router.get("/events/latest-timestamp", response_class=JSONResponse, tags=["Events", "Schedulers"])
def get_latest_event_timestamp_route(
    event_type: Optional[str] = Query(None, alias="type", description="Optional event type to filter by.")
):
    """
    Retrieves the timestamp of the most recently stored event.
    Can be filtered by a specific event type using the 'type' query parameter.
    
    This is used by schedulers to determine the starting point for fetching new events,
    preventing the re-processing of old data.
    """
    logger.info(f"Request received for the latest event timestamp. Type filter: {event_type}")
    # Pass the event_type to the service layer.
    result = get_latest_event_timestamp_data(event_type=event_type)
    return JSONResponse(content=result, status_code=200)

@router.get("/events/for-recognition", response_model=Dict[str, Any], tags=["Facial Recognition"])
def get_events_for_facial_recognition_route(limit: int = Query(100, ge=1, le=1000)):
    """
    Retrieves events that need facial recognition processing.
    """
    return get_events_for_facial_recognition_data(limit=limit)


@router.post("/events/with-recognition", response_class=JSONResponse, tags=["Facial Recognition"])
def update_events_with_recognition_route(request: EventFacialRecognitionUpdateRequest):
    """
    Updates a batch of events with their facial recognition data.
    """
    resp = update_events_with_facial_recognition_data(request)
    if resp:
        return JSONResponse(content=resp, status_code=200)
    else:
        return JSONResponse(content={}, status_code=503)

# ADD THIS NEW ENDPOINT
@router.get("/get-presigned-url", response_model=str, summary="Get S3 Presigned URL")
def get_presigned_url(s3_key: str = Query(..., alias="s3Key", description="The S3 object key for the image.")):
    """
    Generates a temporary, presigned URL to access an S3 object.
    This allows the frontend to securely download and display images directly from S3.
    """
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3Key parameter is required.")

    url = get_presigned_url_for_s3_key(s3_key)

    if not url:
        raise HTTPException(status_code=404, detail="Could not generate URL. The object may not exist or there was a server error.")

    return url