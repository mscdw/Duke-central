from app.crud.event_operations import insert_events
from app.models.event_models import EventRequest
from app.core.logging import get_logger
from typing import Dict, Any, List

logger = get_logger("event-services")

def store_events_data(request: EventRequest) -> Dict[str, Any] | None:
    """
    Processes and passes event data to the CRUD layer for storage.
    This service iterates through events, allowing for future per-event
    processing, before performing a single bulk insert.
    """
    if not request.events:
        logger.warning("Received request to store an empty list of events.")
        return {"message": "No events provided to store.", "stored_count": 0}

    # Prepare events for insertion. This loop makes the service more extensible
    # by allowing for future transformations or validations on a per-event basis,
    # aligning with the pattern used in appearance_services.
    events_to_store: List[Dict[str, Any]] = [event for event in request.events]

    try:
        stored_count = insert_events(events_to_store)
        logger.info(f"Successfully stored {stored_count} events.")
        return {"message": f"Successfully stored {stored_count} events.", "stored_count": stored_count}
    except Exception as e:
        logger.error(f"Could not store events. Details: {e}")
        return None