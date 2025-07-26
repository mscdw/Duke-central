from pymongo import UpdateOne
from app.db.mongodb import db  # Assuming db is initialized here
from typing import List, Dict, Any, Optional
from app.core.logging import get_logger
from app.models.event_models import EventResponse  # EventMediaUpdate is not directly used here
from bson import ObjectId
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()
logger = get_logger("event-operations")

# # --- NO CHANGES TO THIS FUNCTION ---
# def insert_events(events: List[Dict[str, Any]]) -> int:
#     """
#     Inserts a list of event documents into the 'events' collection.
#     """
#     if not events:
#         return 0
#     collection = db["events"]
#     result = collection.insert_many(events)
#     return len(result.inserted_ids)

def insert_events(events: List[Dict[str, Any]]) -> int:
    """
    Inserts or updates a list of event documents into the 'events' collection
    using an idempotent 'upsert' operation based on a compound unique key.
    This prevents duplicate records.

    Each event must contain the fields that make up the unique key:
    'originatingServerId', 'timestamp', 'cameraId', 'type', and 'thisId'.
    """
    if not events:
        return 0

    collection = db["events"]
    bulk_operations = []

    for event in events:
        # --- BUILD THE COMPOUND FILTER ---
        # The filter document must match the fields in your compound unique index.
        try:
            filter_doc = {
                "originatingServerId": event["originatingServerId"],
                "timestamp": event["timestamp"],
                "type": event["type"],
                "thisId": event["thisId"],
                "originatingEventId": event["originatingEventId"]
            }
        except KeyError as e:
            # If an event is missing a key part, we cannot process it.
            logger.warning(f"Skipping event due to missing key field for compound index: {e}. Event data: {event}")
            continue
        # --- END OF COMPOUND FILTER ---
        
        # The update document sets all the fields from the event.
        # There's no need to add a separate 'source_id' field anymore,
        # as the uniqueness is guaranteed by the combination of existing fields.
        event_data_to_set = event.copy()

        # Using UpdateOne with upsert=True:
        # - If a document matching the 5-field filter exists, it gets updated.
        # - If it does NOT exist, a new document is inserted with all fields.
        bulk_operations.append(
            UpdateOne(filter_doc, {"$set": event_data_to_set}, upsert=True)
        )
    
    if not bulk_operations:
        return 0

    try:
        result = collection.bulk_write(bulk_operations, ordered=False)
        # We care about new documents (upserted) and existing documents that were changed (modified).
        # In most cases of re-processing, modified_count will be 0, which is correct.
        stored_count = result.upserted_count + result.modified_count
        logger.info(f"Bulk write result: {result.upserted_count} upserted, {result.modified_count} modified.")
        return stored_count
    except Exception as e:
        logger.error(f"Error during bulk upsert of events: {e}", exc_info=True)
        # Re-raise the exception so the calling service knows the operation failed.
        raise

def get_events_for_enrichment(event_type: str, limit: int) -> List[Dict[str, Any]]:
    """
    Retrieves events of a specific type that need media enrichment.
    An event needs enrichment if it does not have an 's3ImageKey'.
    """
    collection = db["events"]
    query = {
        "type": event_type,
        # The event should not already have an S3 key.
        "s3ImageKey": {"$exists": False},
        # It must have the necessary fields to fetch media.
        "cameraId": {"$exists": True, "$ne": None},
        "timestamp": {"$exists": True, "$ne": None},
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
    Performs a bulk update of events with an s3ImageKey.
    """
    if not updates:
        return 0
    collection = db["events"]
    bulk_operations = []
    for update in updates:
        event_id = update.get("eventId")
        s3_key = update.get("s3ImageKey")
        if event_id and s3_key:
            bulk_operations.append(UpdateOne({"_id": ObjectId(event_id)}, {"$set": {"s3ImageKey": s3_key}}))

    if not bulk_operations:
        return 0
    result = collection.bulk_write(bulk_operations, ordered=False)
    return result.modified_count

# --- 1. FIRST CHANGE: UPDATED QUERY LOGIC ---
def get_events_for_facial_recognition(limit: int) -> List[Dict[str, Any]]:
    """
    Retrieves events that have an image in S3 and have NOT yet been processed for faces.
    An event is considered "unprocessed" if the 'processed_at' field does not exist.
    """
    collection = db["events"]
    
    # The new query correctly identifies unprocessed events.
    query = {
        # Condition 1: Must have an image in S3 to process.
        "s3ImageKey": {"$exists": True, "$ne": ""},
        
        # Condition 2: The 'processed_at' marker must NOT exist.
        "processed_at": {"$exists": False}
    }

    # Retrieve the fields necessary for the recognition process: the ID and the S3 key.
    projection = {"_id": 1, "s3ImageKey": 1}
    
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
    types: Optional[List[str]] = None,
    camera_id: Optional[str] = None,
    face_id: Optional[str] = None,
    # --- START OF CHANGE ---
    user_id: Optional[str] = None,
    user_id_only: bool = False,
    include_events_without_image: bool = False,
    event_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves events, optionally filtering by various criteria.
    """
    collection = db["events"]
    pipeline = []
    
    # If a specific eventId is provided, it's a direct lookup.
    # This is much more efficient than applying all other filters.
    if event_id:
        try:
            # The eventId from the API is a string, but it corresponds to the _id ObjectId.
            obj_id = ObjectId(event_id)
            pipeline.append({"$match": {"_id": obj_id}})
        except Exception:
            # If the event_id is not a valid ObjectId, no results will be found.
            logger.warning(f"Invalid eventId format received: {event_id}. Must be a 24-character hex string.")
            return []
    else:
        # Apply general filters if no specific eventId is given.
        pipeline.append({"$addFields": {"event_date": {"$toDate": "$timestamp"}}})

        match_filter = {}

        if types:
            match_filter["type"] = {"$in": types}
        else:
            match_filter["type"] = {"$in": ["CUSTOM_APPEARANCE", "DEVICE_CLASSIFIED_OBJECT_MOTION_START", "DEVICE_CLASSIFIED_OBJECT_MOTION_STOP", "DEVICE_FACET_START", "DEVICE_FACET_STOP", "DEVICE_FACE_MATCH_START", "DEVICE_FACE_MATCH_STOP", "DEVICE_UNUSUAL_STARTED", "DEVICE_UNUSUAL_STOPPED"]}

        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date

        if date_filter:
            match_filter["event_date"] = date_filter

        if camera_id:
            match_filter["cameraId"] = camera_id

        if not include_events_without_image:
            # Filter for events that have a non-empty s3ImageKey
            match_filter["s3ImageKey"] = {"$exists": True, "$ne": None, "$ne": ""}

        if face_id:
            # MongoDB's dot notation allows us to query for a value within an array of objects.
            match_filter["detected_faces.face_info.FaceId"] = face_id

        if user_id:
            # Filter for events where at least one detected face has the specified userId
            match_filter["detected_faces.userId"] = user_id

        if user_id_only:
            # Filter for events that have at least one face with a non-null userId
            match_filter["detected_faces.userId"] = {"$exists": True, "$ne": None}

        if match_filter:
            pipeline.append({"$match": match_filter})

        # Sort by most recent first
        pipeline.append({"$sort": {"event_date": -1}})

    # The $project stage remains the same
    pipeline.append(
        {
            "$project": {
                "_id": 0,
                "eventId": {"$toString": "$_id"},
                "type": "$type",
                "cameraId": "$cameraId",
                "s3ImageKey": "$s3ImageKey",
                "timestamp": "$timestamp",
                "processed_at": "$processed_at",
                "detected_faces": "$detected_faces"
            }
        }
    )

    events_cursor = collection.aggregate(pipeline)
    return list(events_cursor)

# --- NEW FUNCTION ADDED FOR "SMARTER" SCHEDULER ---
def get_latest_event_timestamp(event_type: Optional[str] = None) -> Optional[str]:
    """
    Finds the timestamp of the most recent event stored in the database.
    This is used by schedulers to determine their starting point.

    Args:
        event_type (Optional[str]): If provided, finds the latest timestamp
                                     ONLY for events of this specific type.
    """
    collection = db["events"]
    
    # Build the filter dynamically. If no type is provided, it's an empty filter.
    filter_doc = {}
    if event_type:
        filter_doc["type"] = event_type
    
    # Efficiently find the single latest document by sorting descending and limiting to 1.
    # We only need the 'timestamp' field.
    latest_event = collection.find_one(
        filter=filter_doc, # Use the dynamically built filter
        projection={"timestamp": 1}, 
        sort=[("timestamp", -1)]
    )
    
    # Return the timestamp string if an event is found, otherwise return None.
    if latest_event:
        return latest_event.get("timestamp")
    return None


def update_event_user_id_in_db(source_user_id: str, target_user_id: str) -> int:
    """
    Finds all events associated with a source_user_id and updates them to the target_user_id.
    This is used during a user merge operation.

    Args:
        source_user_id: The original user ID to find in 'detected_faces.userId'.
        target_user_id: The new user ID to set.

    Returns:
        The number of documents modified.
    """
    logger.info(f"Updating event records from userId '{source_user_id}' to '{target_user_id}'.")
    result = db["events"].update_many(
        {"detected_faces.userId": source_user_id},
        {"$set": {"detected_faces.$[elem].userId": target_user_id}},
        array_filters=[{"elem.userId": source_user_id}]
    )
    logger.info(f"DB update result for repointing event userIds: modified_count={result.modified_count}")
    return result.modified_count
