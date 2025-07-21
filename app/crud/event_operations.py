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


def get_events_for_facial_recognition(limit: int) -> List[Dict[str, Any]]:
    """
    Retrieves events that have an image and have NOT yet been processed for
    facial recognition. An event is considered "processed" if the
    'face_processing' field exists.

    Args:
        limit: The maximum number of events to return.

    Returns:
        A list of event documents that need facial recognition.
    """
    collection = db["events"]
    
    # --- THIS IS THE CORRECTED QUERY ---
    query = {
        # Condition 1: The event must have an image to process.
        "imageBaseString": {"$ne": None},
        
        # Condition 2: The 'face_processing' field must NOT exist.
        # This is the new, robust way to identify unprocessed events.
        "face_processing": {"$exists": False}
    }

    # The rest of the function remains the same
    events_cursor = collection.find(query).limit(limit)

    events_list = []
    for event in events_cursor:
        if "_id" in event and isinstance(event["_id"], ObjectId):
            event["_id"] = str(event["_id"])
        events_list.append(event)

    return events_list


def bulk_update_events_with_facial_recognition(updates: List[Dict[str, Any]]) -> int:
    """
    Performs a bulk update of events with facial recognition data, including
    the new face_processing status object.

    Args:
        updates: A list of update dictionaries, each created from the
                 EventFacialRecognitionUpdate Pydantic model.

    Returns:
        The number of documents modified.
    """
    if not updates:
        return 0

    collection = db["events"]
    bulk_operations = []

    for update in updates:
        # We only need the eventId to proceed.
        event_id = update.get("eventId")
        if not event_id:
            # Skip any malformed update requests without an ID
            continue
            
        # --- FIX ---
        # Construct the payload with ALL the fields from the request.
        # This now includes personId, personFace, AND face_processing.
        set_payload = {
            "personId": update.get("personId"),
            "personFace": update.get("personFace"),
            "face_processing": update.get("face_processing")
        }

        # Optional but highly recommended: Remove keys with None values to keep DB clean.
        # This prevents storing "personId": null in the database.
        set_payload = {k: v for k, v in set_payload.items() if v is not None}
        
        # Only add an update operation if there's something to set.
        if set_payload:
            bulk_operations.append(
                UpdateOne({"_id": ObjectId(event_id)}, {"$set": set_payload})
            )

    if not bulk_operations:
        return 0
    
    # The rest of the function is correct.
    result = collection.bulk_write(bulk_operations, ordered=False)
    return result.modified_count


def get_events(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    include_null_image_base_string: bool = False,
) -> List[EventResponse]:
    """
    Retrieves events from the 'events' collection that fall within a specified date range
    and are ONLY of type 'DEVICE_CLASSIFIED_OBJECT_MOTION_START'.

    Args:
        start_date: Optional start date for the date range filter.
        end_date: Optional end date for the date range filter.
        include_null_image_base_string: If False (default), only returns events
                                       with a non-null imageBaseString.
    """
    collection = db["events"]
    pipeline = []

    # STAGE 1: Convert the 'timestamp' string field into a true BSON Date object.
    pipeline.append({"$addFields": {"event_date": {"$toDate": "$timestamp"}}})

    # STAGE 2: Build the match stage.
    match_filter = {}

    # --- THIS IS THE REQUIRED CHANGE ---
    # Hardcode the filter to only match events of this specific type.
    # The 'title' from the API maps to the 'type' field in the database.
    match_filter["type"] = "DEVICE_CLASSIFIED_OBJECT_MOTION_START"
    # --- END OF CHANGE ---

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

    # STAGE 3: Sort the results by timestamp.
    pipeline.append({"$sort": {"event_date": 1}})

    # STAGE 4: Project the final shape to match the EventResponse model.
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
                "timestamp": "$timestamp"            }
        }
    )

    events_cursor = collection.aggregate(pipeline)
    return list(events_cursor)