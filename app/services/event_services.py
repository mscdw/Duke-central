from app.crud.event_operations import insert_events, get_events_for_enrichment, bulk_update_events_media
from app.models.event_models import EventRequest, EventMediaUpdateRequest
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


def get_events_for_enrichment_data(event_type: str, limit: int) -> Dict[str, Any]:
    """
    Retrieves events that need media enrichment from the CRUD layer.

    Args:
        event_type: The type of event to retrieve.
        limit: The maximum number of events to retrieve.

    Returns:
        A dictionary containing a list of events.
    """
    try:
        events = get_events_for_enrichment(event_type, limit)
        logger.info(f"Found {len(events)} events of type '{event_type}' for media enrichment.")
        return {"events": events}
    except Exception as e:
        logger.error(f"Could not retrieve events for enrichment. Details: {e}", exc_info=True)
        return {"events": []}


def update_events_with_media(request: EventMediaUpdateRequest) -> Dict[str, Any] | None:
    """
    Processes and passes event media updates to the CRUD layer for bulk update.
    """
    if not request.updates:
        logger.warning("Received request to update media for an empty list of events.")
        return {"message": "No event updates provided.", "updated_count": 0}

    updates_to_perform = [update.model_dump() for update in request.updates]
    updated_count = bulk_update_events_media(updates_to_perform)
    logger.info(f"Successfully updated {updated_count} events with media.")
    return {"message": f"Successfully updated {updated_count} events.", "updated_count": updated_count}