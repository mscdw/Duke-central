from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("anomaly-services")

settings = get_settings()
client = MongoClient(settings.MONGODB_BASE) 
db = client[settings.MONGODB_DB]
collection = db["anomaly_reports"]

def get_anomaly_reports_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    personId: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Queries the 'anomaly-reports' collection in MongoDB based on filter criteria.
    """
    query = {}
    
    # This is the real query logic
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["profile_date"] = date_filter
            
    if personId:
        query["personId"] = personId
        
    logger.info(f"Executing anomaly query: {query}")
        
    try:
        reports_cursor = collection.find(query).sort("profile_date", -1)
        reports_list = list(reports_cursor)
        logger.info(f"MongoDB query found {len(reports_list)} documents.")
        
        # Process the list for Pydantic
        for doc in reports_list:
            doc["_id"] = str(doc["_id"])
            for log_entry in doc.get('activity_log', []):
                if isinstance(log_entry.get("sighting_start"), dict) and "$date" in log_entry["sighting_start"]:
                     log_entry["sighting_start"] = log_entry["sighting_start"]["$date"]
                if isinstance(log_entry.get("sighting_end"), dict) and "$date" in log_entry["sighting_end"]:
                     log_entry["sighting_end"] = log_entry["sighting_end"]["$date"]
        
        return reports_list
    except Exception as e:
        logger.error(f"Error querying anomaly reports from MongoDB: {e}")
        return []
