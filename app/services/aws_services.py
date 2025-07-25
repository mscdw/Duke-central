import boto3
import io
from PIL import Image, ImageDraw
from botocore.exceptions import ClientError
from typing import Optional, List, Dict, Any
from app.models.appearance_models import FaceInfo, BoundingBox
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger("aws-services")
settings = get_settings()

DEFAULT_COLLECTION_ID = 'new-face-collection-2'

rekognition = boto3.client("rekognition", region_name="us-east-2")

def create_collection(collection_id: str = DEFAULT_COLLECTION_ID):
    """Create a new Rekognition collection."""
    try:
        response = rekognition.create_collection(CollectionId=collection_id)
        logger.info(f"CreateCollection response: {response}")
        return response
    except ClientError as e:
        logger.error(f"Error creating collection {collection_id}: {e}")
        raise

def delete_collection(collection_id: str = DEFAULT_COLLECTION_ID):
    """Delete the Rekognition collection."""
    try:
        response = rekognition.delete_collection(CollectionId=collection_id)
        logger.info(f"DeleteCollection response: {response}")
        return response
    except ClientError as e:
        logger.error(f"Error deleting collection {collection_id}: {e}")
        raise

def list_collections():
    """List all Rekognition collections."""
    try:
        response = rekognition.list_collections()
        collections = response.get("CollectionIds", [])
        logger.info(f"Collections: {collections}")
        return collections
    except ClientError as e:
        logger.error(f"Error listing collections: {e}")
        raise

def collection_exists(collection_id: str = DEFAULT_COLLECTION_ID) -> bool:
    """Check if the collection exists."""
    try:
        collections = list_collections()
        return collection_id in collections
    except Exception as e:
        logger.error(f"Error checking if collection exists: {e}")
        return False

def list_users(collection_id: str = DEFAULT_COLLECTION_ID) -> List[Dict[str, Any]]:
    """
    Lists all users from a Rekognition collection, handling pagination automatically.
    Returns a list of user dictionaries.
    """
    all_users = []
    try:
        paginator = rekognition.get_paginator('list_users')
        pages = paginator.paginate(CollectionId=collection_id)
        for page in pages:
            all_users.extend(page.get('Users', []))
        logger.info(f"Found {len(all_users)} users in Rekognition collection '{collection_id}'.")
        return all_users
    except ClientError as e:
        logger.error(f"Failed to list users from Rekognition collection '{collection_id}': {e.response['Error']['Message']}", exc_info=True)
        raise # Re-raise so the API layer can handle it.


def search_faces_by_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, face_match_threshold: float = 90.0, max_faces: int = 1):
    """Search for faces in the collection using an image."""
    try:
        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            FaceMatchThreshold=face_match_threshold,
            MaxFaces=max_faces
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidParameterException' and "no faces in the image" in e.response['Error']['Message']:
            logger.info("Rekognition confirmed no face in image. This is a valid outcome.")
            return None
        else:
            logger.error(f"Error searching faces: {e}")
            raise

def index_faces(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, max_faces: int = 1):
    """Index faces in an image to the collection."""
    try:
        response = rekognition.index_faces(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            MaxFaces=max_faces
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidParameterException' and "no faces in the image" in e.response['Error']['Message']:
            logger.info("Rekognition confirmed no face in image for indexing. This is a valid outcome.")
            return None
        else:
            logger.error(f"Error indexing faces: {e}")
            raise

def process_face_search_and_index(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID) -> FaceInfo | None:
    """
    Process an image by first searching for existing faces, then indexing if no match found.
    Returns FaceInfo if a face is found/indexed, None if no face detected.
    """
    try:
        # First, try to search for existing faces
        search_response = search_faces_by_image(image_bytes, collection_id)
        
        if search_response:
            face_matches = search_response.get("FaceMatches", [])
            if face_matches:
                logger.info("Face MATCHED in collection")
                bbox_data = search_response.get("SearchedFaceBoundingBox")
                matched_face_data = face_matches[0]["Face"]
                return FaceInfo(
                    FaceId=matched_face_data.get("FaceId"),
                    BoundingBox=BoundingBox(**bbox_data),
                    ImageId=matched_face_data.get("ImageId"),
                    Confidence=matched_face_data.get("Confidence")
                )
        
        # No match found, try to index as new face
        logger.info("No match found. Indexing as new face.")
        index_response = index_faces(image_bytes, collection_id)
        
        if index_response:
            face_records = index_response.get('FaceRecords') or []
            if face_records:
                logger.info("New face INDEXED successfully")
                face = face_records[0]['Face']
                bbox = face.get("BoundingBox", {})
                return FaceInfo(
                    FaceId=face.get("FaceId"),
                    BoundingBox=BoundingBox(**bbox),
                    ImageId=face.get("ImageId"),
                    Confidence=face.get("Confidence", 0.0)
                )
        
        # No face detected in image
        logger.warning("No face could be detected in the image")
        return None
        
    except Exception as e:
        logger.error(f"Error processing face search and index: {e}")
        raise

def save_cropped_face(image_bytes: bytes, bbox_normalized: BoundingBox, original_width: int, original_height: int, output_filename: str = "crop.png"):
    """Save a cropped face from an image using bounding box coordinates."""
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

# --- S3-related functionality ---
try:
    s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
    S3_BUCKET_NAME = settings.S3_FACE_IMAGE_BUCKET
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}", exc_info=True)
    s3_client = None
    S3_BUCKET_NAME = None

def create_presigned_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL to share an S3 object.

    :param s3_key: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    if not all([s3_client, S3_BUCKET_NAME]):
        logger.error("S3 client or bucket not configured. Cannot create presigned URL.")
        return None

    try:
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key}, ExpiresIn=expiration)
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for key {s3_key}: {e}", exc_info=True)
        return None
    return response
