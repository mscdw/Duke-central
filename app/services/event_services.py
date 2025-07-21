# --- 1. IMPORT THE NEW CRUD FUNCTION ---
from app.crud.event_operations import (
    insert_events, 
    get_events_for_enrichment, 
    bulk_update_events_media, 
    get_events, 
    get_events_for_facial_recognition, 
    bulk_update_events_with_facial_recognition,
    get_latest_event_timestamp  # <-- Add this import
)
from app.models.event_models import EventRequest, EventMediaUpdateRequest, EventFacialRecognitionUpdateRequest
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = get_logger("event-services")

# --- NO CHANGES TO ANY OF THE EXISTING FUNCTIONS ---

def store_events_data(request: EventRequest) -> Dict[str, Any] | None:
    """
    Processes and passes event data to the CRUD layer for storage.
    """
    if not request.events:
        logger.warning("Received request to store an empty list of events.")
        return {"message": "No events provided to store.", "stored_count": 0}

    events_to_store: List[Dict[str, Any]] = [event for event in request.events]

    try:
        stored_count = insert_events(events_to_store)
        logger.info(f"Successfully stored {stored_count} events.")
        return {"message": f"Successfully stored {stored_count} events.", "stored_count": stored_count}
    except Exception as e:
        logger.error(f"Could not store events. Details: {e}")
        return None


def get_events_data(
    start_date: Optional[datetime], 
    end_date: Optional[datetime],
    types: Optional[List[str]] = None,
    face_id: Optional[str] = None  # <-- Add face_id parameter
) -> List[Dict[str, Any]] | None:
    """
    Retrieves events, optionally filtered by type and Face ID, from the CRUD layer.
    """
    try:
        # Pass the new parameter down to the CRUD function
        events = get_events(
            start_date=start_date, 
            end_date=end_date, 
            types=types, 
            face_id=face_id
        )
        logger.info(f"Retrieved {len(events)} events for query.")
        return events
    except Exception as e:
        logger.error(f"Could not retrieve events. Details: {e}", exc_info=True)
        return None

def get_events_for_enrichment_data(event_type: str, limit: int) -> Dict[str, Any]:
    """
    Retrieves events that need media enrichment from the CRUD layer.
    """
    try:
        events = get_events_for_enrichment(event_type, limit)
        logger.info(f"Found {len(events)} events of type '{event_type}' for media enrichment.")
        return {"events": events}
    except Exception as e:
        logger.error(f"Could not retrieve events for enrichment. Details: {e}", exc_info=True)
        return {"events": []}


def get_events_for_facial_recognition_data(limit: int) -> Dict[str, Any]:
    """
    Retrieves events that need facial recognition from the CRUD layer.
    """
    try:
        events = get_events_for_facial_recognition(limit)
        logger.info(f"Found {len(events)} events for facial recognition.")
        return {"events": events}
    except Exception as e:
        logger.error(f"Could not retrieve events for facial recognition. Details: {e}", exc_info=True)
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


def update_events_with_facial_recognition_data(request: EventFacialRecognitionUpdateRequest) -> Dict[str, Any] | None:
    """
    Processes and passes event facial recognition updates to the CRUD layer for bulk update.
    """
    if not request.updates:
        logger.warning("Received request to update facial recognition for an empty list of events.")
        return {"message": "No event updates provided.", "updated_count": 0}

    updates_to_perform = [update.model_dump() for update in request.updates]

    try:
        updated_count = bulk_update_events_with_facial_recognition(updates_to_perform)
        logger.info(f"Successfully updated {updated_count} events with facial recognition data.")
        return {"message": f"Successfully updated {updated_count} events.", "updated_count": updated_count}
    except Exception as e:
        logger.error(f"Could not update events with facial recognition data. Details: {e}", exc_info=True)
        return None

# --- 2. ADD THE NEW SERVICE FUNCTION ---
def get_latest_event_timestamp_data(event_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Service layer function to retrieve the latest event timestamp from the CRUD layer.
    Can be filtered by a specific event type.
    """
    try:
        # Pass the event_type down to the CRUD function
        timestamp = get_latest_event_timestamp(event_type=event_type)
        # The response is wrapped in a dictionary to be JSON-friendly for the API.
        return {"latest_timestamp": timestamp}
    except Exception as e:
        logger.error(f"Could not retrieve latest event timestamp. Details: {e}", exc_info=True)
        # Return a null timestamp in case of an error, so the scheduler can handle it.
        return {"latest_timestamp": None}