# app/services/visualization_services.py

from typing import Optional, Dict, Any
from pymongo import MongoClient
from app.core.config import get_settings
from app.core.logging import get_logger

# Use a specific logger for this service
logger = get_logger("visualization-services")

# Establish database connection using the same pattern
settings = get_settings()
client = MongoClient(settings.MONGODB_BASE) 
db = client[settings.MONGODB_DB]
# Point to the new 'visualizations' collection
collection = db["visualizations"]

def get_visualization_data_by_run_id(
    run_id: str
) -> Optional[Dict[str, Any]]:
    """
    Queries the 'visualizations' collection in MongoDB for a single document
    matching the provided run_id.
    """
    # The query is simple: find the document with the matching run_id
    query = {"run_id": run_id}
    
    logger.info(f"Executing visualization query: {query}")
        
    try:
        # Use find_one() as we expect only one document per run_id
        document = collection.find_one(query)
        
        if document:
            logger.info(f"MongoDB query found a document for run_id: {run_id}")
            
            # Process the document for Pydantic/FastAPI compatibility
            # This is crucial for JSON serialization.
            document["_id"] = str(document["_id"])
            
            # The 'created_at' field is likely an ISODate object, which
            # FastAPI's Pydantic model can handle automatically, so no special
            # conversion is needed here unlike the anomaly service's activity_log.
            
            return document
        else:
            logger.warning(f"No visualization found in MongoDB for run_id: {run_id}")
            return None # Return None if no document is found

    except Exception as e:
        logger.error(f"Error querying visualization for run_id {run_id} from MongoDB: {e}")
        return None # Return None on a database error