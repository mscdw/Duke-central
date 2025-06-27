import boto3
import base64
from datetime import datetime, time, timedelta
from app.services.appearance_services import get_appearances_data
from app.db.mongodb import db
from app.models.appearance_models import FaceInfo, BoundingBox
import sys
from app.core.logging import get_logger
import io
from PIL import Image, ImageDraw
from botocore.exceptions import ClientError

logger = get_logger("central-base")
rekognition = boto3.client("rekognition")
collection_id = 'new-face-collection-2'

def create_collection():
    response = rekognition.create_collection(CollectionId=collection_id)
    logger.info(f"CreateCollection response: {response}")
    return response

def delete_collection():
    response = rekognition.delete_collection(CollectionId=collection_id)
    logger.info(f"DeleteCollection response: {response}")
    return response

def list_collections():
    response = rekognition.list_collections()
    logger.info("Collections:", response.get("CollectionIds", []))
    return response.get("CollectionIds", [])

def save_cropped_face(image_bytes: bytes, bbox_normalized: BoundingBox, original_width: int, original_height: int, output_filename: str = "crop.png"):
    try:
        original_image = Image.open(io.BytesIO(image_bytes))
        original_image.save("original_for_debug.png")
        logger.info("Saved ./original_for_debug.png for verification.")
        pixel_box = bbox_normalized.to_pixel_box(original_width, original_height)
        logger.info(f"CALCULATED PIXEL BOX for cropping: {pixel_box}")
        image_with_box = original_image.copy()
        draw = ImageDraw.Draw(image_with_box)
        draw.rectangle(pixel_box, outline="red", width=3)
        image_with_box.save("debug_box_on_original.png")
        logger.info("Saved ./debug_box_on_original.png to show the calculated crop area.")
        cropped_image = original_image.crop(pixel_box)
        cropped_image.save(output_filename)
        logger.info(f"Successfully saved final cropped image to ./{output_filename}")
    except Exception as e:
        logger.error(f"An error occurred during the save_cropped_face process: {e}", exc_info=True)

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
            try:
                search_response = rekognition.search_faces_by_image(
                    CollectionId=collection_id,
                    Image={'Bytes': image_bytes},
                    FaceMatchThreshold=90,
                    MaxFaces=1
                )
                face_matches = search_response.get("FaceMatches", [])
                if face_matches:
                    logger.info(f"Face MATCHED for event {event.get('_id')}")
                    bbox_data = search_response.get("SearchedFaceBoundingBox")
                    matched_face_data = face_matches[0]["Face"]
                    if bbox_data:
                        face_info = FaceInfo(
                            FaceId=matched_face_data.get("FaceId"),
                            BoundingBox=BoundingBox(**bbox_data),
                            ImageId=matched_face_data.get("ImageId"),
                            Confidence=matched_face_data.get("Confidence")
                        )
                else:
                    logger.info(f"No match found for event {event.get('_id')}. Indexing as new face.")
                    index_response = rekognition.index_faces(
                        CollectionId=collection_id,
                        Image={'Bytes': image_bytes},
                        MaxFaces=1
                    )
                    face_records = index_response.get('FaceRecords') or []
                    if face_records:
                        logger.info(f"New face INDEXED for event {event.get('_id')}")
                        face = face_records[0]['Face']
                        bbox = face.get("BoundingBox", {})
                        face_info = FaceInfo(
                            FaceId=face.get("FaceId"),
                            BoundingBox=BoundingBox(**bbox),
                            ImageId=face.get("ImageId"),
                            Confidence=face.get("Confidence", 0.0)
                        )
            except ClientError as e:
                if e.response['Error']['Code'] == 'InvalidParameterException' and "no faces in the image" in e.response['Error']['Message']:
                    logger.info(f"Rekognition confirmed no face in image for event {event.get('_id')}. This is a valid outcome.")
                else:
                    raise e
            
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
