from app.db.mongodb import db
from typing import List, Dict, Any, Optional
from app.core.logging import get_logger
from app.models.event_models import EventMediaUpdate, EventResponse
from bson import ObjectId
from datetime import datetime
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


def get_events(start_date: Optional[datetime], end_date: Optional[datetime]) -> List[EventResponse]:
    """
    Retrieves events from the 'events' collection that fall within a specified date range.
    This version is corrected to match the actual database schema and $project rules.
    """
    collection = db["events"]
    pipeline = []

    # STAGE 1: Convert the 'timestamp' string field into a true BSON Date object.
    pipeline.append({
        "$addFields": {
            "event_date": {"$toDate": "$timestamp"}
        }
    })

    # STAGE 2: Build the match stage using the new 'event_date' field.
    match_filter = {}
    if start_date:
        match_filter["$gte"] = start_date
    if end_date:
        match_filter["$lte"] = end_date

    if match_filter:
        pipeline.append({"$match": {"event_date": match_filter}})

    # STAGE 3: Sort the results by timestamp.
    pipeline.append({"$sort": {"event_date": 1}})

    # STAGE 4: Project the final shape to match the EventResponse model.
    # THIS STAGE CONTAINS THE FIX.
    pipeline.append({
        "$project": {
            "_id": 0,
            "eventId": {"$toString": "$_id"},
            "title": "$type",
            "start": "$timestamp",
            "end": "$timestamp",
            # Use $literal to assign a boolean value instead of excluding the field.
            "allDay": {"$literal": False},
            "is_all_day": {"$literal": False}
        }
    })

    events_cursor = collection.aggregate(pipeline)
    return list(events_cursor)