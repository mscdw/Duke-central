"""
AWS Rekognition Collection Management Script

This script provides command-line utilities for managing AWS Rekognition collections.

Usage:
    python -m app.scripts.manage_collections.py create <collection_id>
    python -m app.scripts.manage_collections.py delete <collection_id>
    python -m app.scripts.manage_collections.py list
"""

import sys
from app.services.aws_services import create_collection, delete_collection, list_collections
from app.core.logging import get_logger

logger = get_logger("collection-manager")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        collections = list_collections()
        print(f"Found {len(collections)} collections:")
        for collection in collections:
            print(f"  - {collection}")
    
    elif command == "create":
        if len(sys.argv) != 3:
            print("Usage: python manage_collections.py create <collection_id>")
            sys.exit(1)
        
        collection_id = sys.argv[2]
        try:
            response = create_collection(collection_id)
            print(f"Successfully created collection: {response}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            sys.exit(1)
    
    elif command == "delete":
        if len(sys.argv) != 3:
            print("Usage: python manage_collections.py delete <collection_id>")
            sys.exit(1)
        
        collection_id = sys.argv[2]
        try:
            response = delete_collection(collection_id)
            print(f"Successfully deleted collection: {response}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
