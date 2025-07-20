from app.db.mongodb import db
from typing import List, Dict, Any
from app.core.logging import get_logger

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