import base64
from datetime import datetime, time, timedelta
from app.services.appearance_services import get_appearances_data
from app.services.aws_services import process_face_search_and_index
from app.db.mongodb import db
import sys
from app.core.logging import get_logger

logger = get_logger("central-base")


def index_events_with_rekognition(date_str):
    start_dt = datetime.strptime(date_str, "%Y-%m-%d")
    start_datetime = datetime.combine(start_dt, time.min)
    end_datetime = datetime.combine(start_dt, time(hour=23, minute=59, second=59, microsecond=999))
    events = get_appearances_data(start_datetime, end_datetime)
    updated_count = 0
    removed_count = 0
    no_action_count = 0

    for event in events:
        image_base64 = event.get("imageBaseString")
        if not image_base64:
            continue
        existing_person_id = event.get("personId")
        face_info = None
        try:
            image_bytes = base64.b64decode(image_base64)
            face_info = process_face_search_and_index(image_bytes)
            
            # save_cropped_face(image_bytes, face_info.BoundingBox, original_width, original_height, "crop.png")
            
            if face_info:
                # CASE 1: A face was found (either by search or index).
                db.appearances.update_one(
                    {"_id": event["_id"]},
                    {"$set": {"personId": face_info.FaceId, "personFace": face_info.model_dump()}}
                )
                logger.info(f"Successfully SET/updated personId {face_info.FaceId} for event {event['_id']}")
                updated_count += 1
            else:
                # CASE 2: No face was found in the image by Rekognition.
                logger.warning(f"No face could be detected in the image for event {event['_id']}")
                if existing_person_id:
                    # If so, use $unset to completely remove the fields.
                    db.appearances.update_one(
                        {"_id": event["_id"]},
                        {"$unset": {"personId": "", "personFace": ""}}
                    )
                    logger.warning(f"REMOVED stale personId ({existing_person_id}) from event {event['_id']}")
                    removed_count += 1
                else:
                    # If there was no existing personId, we don't need to do anything.
                    logger.info(f"No prior personId found for event {event['_id']}. No action taken.")
                    no_action_count += 1
        except Exception as e:
            logger.info(f"Error processing event {event.get('_id')}: {e}")

    logger.info("--- Processing Summary ---")
    logger.info(f"Date: {date_str}")
    logger.info(f"Records Updated/Set: {updated_count}")
    logger.info(f"Stale Records Cleaned (Removed): {removed_count}")
    logger.info(f"Records with No Face (No Action): {no_action_count}")
    logger.info("--------------------------")

def run_for_date_range(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    current_date = start_date
    while current_date <= end_date:
        formatted_date = current_date.strftime("%Y-%m-%d")
        print(f"Running for date: {formatted_date}")
        index_events_with_rekognition(formatted_date)
        current_date += timedelta(days=1)

if __name__ == "__main__":
    args = sys.argv
    if len(args) == 3:
        run_for_date_range(args[1], args[2])
    else:
        print("Usage: python app/scripts/index_events_with_rekognition.py <YYYY-MM-DD> <YYYY-MM-DD>")
        exit(1)
