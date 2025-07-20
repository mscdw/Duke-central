from app.db.mongodb import db
from typing import List, Dict, Any
from app.core.logging import get_logger
from app.models.event_models import EventMediaUpdate
from bson import ObjectId
from pymongo import UpdateOne

logger = get_logger("event-operations")

def insert_events(events: List[Dict[str, Any]]) -> int:
    """
    Inserts a list of event documents into the 'events' collection.

    Args:
        events: A list of event dictionaries to insert.

    Returns:
        The number of documents inserted.

    Raises:
        Exception: For any database insertion errors.
    """
    if not events:
        return 0

    collection = db["events"]
    result = collection.insert_many(events)
    return len(result.inserted_ids)


def get_events_for_enrichment(event_type: str, limit: int) -> List[Dict[str, Any]]:
    """
    Retrieves events that need media enrichment.

    Args:
        event_type: The type of event to look for.
        limit: The maximum number of events to return.

    Returns:
        A list of event documents that need media enrichment.
    """
    collection = db["events"]
    query = {
        "type": event_type,
        "$or": [
            {"imageBaseString": None},
            {"json": None},
        ],
    }
    events_cursor = collection.find(query).limit(limit)
    
    events_list = []
    for event in events_cursor:
        if "_id" in event and isinstance(event["_id"], ObjectId):
            event["_id"] = str(event["_id"])
        events_list.append(event)
        
    return events_list


def bulk_update_events_media(updates: List[Dict[str, Any]]) -> int:
    """
    Performs a bulk update of events with media data.

    Args:
        updates: A list of update dictionaries, each containing 'eventId'
                 and media data ('imageBaseString', 'json').

    Returns:
        The number of documents modified.
    """
    if not updates:
        return 0

    collection = db["events"]

    bulk_operations = []
    for update in updates:
        set_payload = {}
        if update.get("imageBaseString") is not None:
            set_payload["imageBaseString"] = update["imageBaseString"]
        if update.get("json") is not None:
            set_payload["json"] = update["json"]

        if set_payload:
            if "eventId" in update and update["eventId"]:
                bulk_operations.append(UpdateOne({"_id": ObjectId(update["eventId"])}, {"$set": set_payload}))

    if not bulk_operations:
        return 0

    result = collection.bulk_write(bulk_operations, ordered=False)
    return result.modified_count