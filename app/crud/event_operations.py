from pymongo import UpdateOne
from app.db.mongodb import db  # Assuming db is initialized here
from typing import List, Dict, Any, Optional
from app.core.logging import get_logger
from app.models.event_models import EventResponse  # EventMediaUpdate is not directly used here
from bson import ObjectId
from datetime import datetime

logger = get_logger("event-operations")

# --- NO CHANGES TO THIS FUNCTION ---
def insert_events(events: List[Dict[str, Any]]) -> int:
    """
    Inserts a list of event documents into the 'events' collection.
    """
    if not events:
        return 0
    collection = db["events"]
    result = collection.insert_many(events)
    return len(result.inserted_ids)

# --- NO CHANGES TO THIS FUNCTION ---
def get_events_for_enrichment(event_type: str, limit: int) -> List[Dict[str, Any]]:
    """
    Retrieves events that need media enrichment.
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

# --- NO CHANGES TO THIS FUNCTION ---
def bulk_update_events_media(updates: List[Dict[str, Any]]) -> int:
    """
    Performs a bulk update of events with media data.
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

# --- 1. FIRST CHANGE: UPDATED QUERY LOGIC ---
def get_events_for_facial_recognition(limit: int) -> List[Dict[str, Any]]:
    """
    Retrieves events that have an image and have NOT yet been processed.
    An event is considered "unprocessed" if the 'processed_at' field does not exist.
    """
    collection = db["events"]
    
    # The new query correctly identifies unprocessed events.
    query = {
        # Condition 1: Must have an image to process.
        "imageBaseString": {"$exists": True, "$ne": ""},
        
        # Condition 2: The 'processed_at' marker must NOT exist.
        "processed_at": {"$exists": False}
    }

    # Only retrieve the fields necessary for the recognition process.
    projection = {"_id": 1, "imageBaseString": 1}
    
    events_cursor = collection.find(query, projection).limit(limit)

    events_list = []
    for event in events_cursor:
        # Convert ObjectId back to string for consumption by the service/scheduler.
        event["_id"] = str(event["_id"])
        events_list.append(event)

    return events_list

# --- 2. SECOND CHANGE: UPDATED UPDATE LOGIC ---
def bulk_update_events_with_facial_recognition(updates: List[Dict[str, Any]]) -> int:
    """
    Performs a bulk update for events with the new multi-face recognition data structure.
    """
    if not updates:
        return 0

    collection = db["events"]
    bulk_operations = []

    for update in updates:
        event_id = update.get("eventId")
        if not event_id:
            continue
            
        # The new update payload directly reflects the new Pydantic model.
        # It sets the processing timestamp and the array of detected faces.
        set_payload = {
            "processed_at": update.get("processed_at"),
            "detected_faces": update.get("detected_faces", []) # Default to empty list
        }
 
        bulk_operations.append(
            UpdateOne({"_id": ObjectId(event_id)}, {"$set": set_payload})
        )

    if not bulk_operations:
        return 0
    
    result = collection.bulk_write(bulk_operations, ordered=False)
    return result.modified_count

# --- NO CHANGES TO THIS FUNCTION ---
def get_events(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    include_null_image_base_string: bool = False,
) -> List[Dict[str, Any]]: # Note: This returns a dict list, not EventResponse objects directly
    """
    Retrieves events from the 'events' collection that fall within a specified date range
    and are ONLY of type 'DEVICE_CLASSIFIED_OBJECT_MOTION_START'.
    """
    collection = db["events"]
    pipeline = []

    pipeline.append({"$addFields": {"event_date": {"$toDate": "$timestamp"}}})

    match_filter = {}
    match_filter["type"] = "DEVICE_CLASSIFIED_OBJECT_MOTION_START"

    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date

    if date_filter:
        match_filter["event_date"] = date_filter

    if not include_null_image_base_string:
        match_filter["imageBaseString"] = {"$ne": None}

    if match_filter:
        pipeline.append({"$match": match_filter})

    pipeline.append({"$sort": {"event_date": 1}})

    pipeline.append(
        {
            "$project": {
                "_id": 0,
                "eventId": {"$toString": "$_id"},
                "title": "$type",
                "start": "$timestamp",
                "end": "$timestamp",
                "allDay": {"$literal": False},
                "is_all_day": {"$literal": False},
                "imageBaseString": "$imageBaseString",
                "timestamp": "$timestamp",
                "processed_at": "$processed_at",       # Pass through the processed_at field
                "detected_faces": "$detected_faces"  # Pass through the detected_faces array
            }
        }
    )

    events_cursor = collection.aggregate(pipeline)
    return list(events_cursor)