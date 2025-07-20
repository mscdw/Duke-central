import json
from fastapi import APIRouter
from fastapi.responses import Response
from app.core.logging import get_logger
from app.models.event_models import EventRequest
from app.services.event_services import store_events_data

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