import boto3
import base64
from datetime import datetime, time
from app.services.appearance_services import get_appearances_data
from app.db.mongodb import db
from app.models.appearance_models import FaceInfo, BoundingBox
import sys

def index_events_with_rekognition(date_str):
    rekognition = boto3.client("rekognition")
    collection_id = 'face-collection'

    start_dt = datetime.strptime(date_str, "%Y-%m-%d")
    start_datetime = datetime.combine(start_dt, time.min)
    end_datetime = datetime.combine(start_dt, time(hour=23, minute=59, second=59, microsecond=999))
    events = get_appearances_data(start_datetime, end_datetime)
    updated = 0
    for event in events:
        image_base64 = event.get("imageBaseString")
        if not image_base64:
            continue
        try:
            image_bytes = base64.b64decode(image_base64)
            search_response = rekognition.search_faces_by_image(
                CollectionId=collection_id,
                Image={'Bytes': image_bytes},
                FaceMatchThreshold=70,
                MaxFaces=1
            )
            if search_response.get("FaceMatches"):
                face = search_response["FaceMatches"][0]["Face"]
                bbox = face.get("BoundingBox", {})
                bounding_box = BoundingBox(
                    Width=bbox.get("Width", 0.0),
                    Height=bbox.get("Height", 0.0),
                    Left=bbox.get("Left", 0.0),
                    Top=bbox.get("Top", 0.0)
                )
                face_info = FaceInfo(
                    FaceId=face.get("FaceId"),
                    BoundingBox=bounding_box,
                    ImageId=face.get("ImageId"),
                    Confidence=face.get("Confidence", 0.0)
                )
            else:
                index_response = rekognition.index_faces(
                    CollectionId=collection_id,
                    Image={'Bytes': image_bytes},
                    MaxFaces=1,
                )
                face_records = index_response.get('FaceRecords', [])
                if not face_records:
                    continue
                face = face_records[0]['Face']
                bbox = face.get("BoundingBox", {})
                bounding_box = BoundingBox(
                    Width=bbox.get("Width", 0.0),
                    Height=bbox.get("Height", 0.0),
                    Left=bbox.get("Left", 0.0),
                    Top=bbox.get("Top", 0.0)
                )
                face_info = FaceInfo(
                    FaceId=face.get("FaceId"),
                    BoundingBox=bounding_box,
                    ImageId=face.get("ImageId"),
                    Confidence=face.get("Confidence", 0.0)
                )
            db.appearances.update_one(
                {"_id": event["_id"]},
                {"$set": {"personId": face_info.FaceId, "personFace": face_info.model_dump()}}
            )
            updated += 1
        except Exception as e:
            print(f"Error processing event {event.get('_id')}: {e}")
    print(f"Updated {updated} events with personId and personFace info for date {date_str}.")

if __name__ == "__main__":
    args = sys.argv
    if len(args) == 2:
        index_events_with_rekognition(args[1])
    else:
        print("Usage: python app/scripts/index_events_with_rekognition.py <YYYY-MM-DD>")
        exit(1)
