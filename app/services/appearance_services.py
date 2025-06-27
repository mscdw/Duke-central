from app.crud.appearance_operations import insert_appearance_events, get_all_appearance_events
from app.models.appearance_models import AppearanceRequest
from app.services.aws_services import process_face_search_and_index
from datetime import datetime
import base64
from app.core.logging import get_logger

logger = get_logger("appearance-services")

def store_appearances_data(request: AppearanceRequest):
    processed_events = []
    faces_processed = 0
    
    for event in request.results:
        processed_event = event.model_copy()
        if event.imageBaseString:
            try:
                image_bytes = base64.b64decode(event.imageBaseString)
                face_info = process_face_search_and_index(image_bytes)        
                if face_info:
                    processed_event.personId = face_info.FaceId
                    processed_event.personFace = face_info
                    faces_processed += 1
                    logger.info(f"Successfully processed face for event {event.objectId} - FaceId: {face_info.FaceId}")
                else:
                    logger.info(f"No face detected for event {event.objectId}")
            except Exception as e:
                logger.error(f"Error processing face for event {event.objectId}: {e}")
        else:
            logger.warning(f"No image data found for event {event.objectId}")
        processed_events.append(processed_event)
    
    insert_appearance_events(processed_events)
    return {
        "inserted": len(processed_events),
        "faces_processed": faces_processed
    }

def get_appearances_data(start_date: datetime = None, end_date: datetime = None, personIdOnly: bool = False, personId: str = None):
    return get_all_appearance_events(start_date, end_date, personIdOnly, personId)
