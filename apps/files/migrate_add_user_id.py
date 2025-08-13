#!/usr/bin/env python3
"""
Migration script to add user_id field to existing files that don't have it.
This script finds files that only have device_id and adds the corresponding user_id.
"""

from pymongo.mongo_client import MongoClient
from datetime import datetime

def migrate_files_add_user_id():
    """
    Add user_id field to existing files that don't have it.
    This looks up the user_id from the device_id field.
    """
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_collection = db["files"]
    device_collection = db["devices"]
    
    print(f"Starting migration at {datetime.now()}")
    
    # Find all files that don't have user_id but have device_id
    files_without_user_id = file_collection.find({
        "user_id": {"$exists": False},
        "device_id": {"$exists": True}
    })
    
    total_files = file_collection.count_documents({
        "user_id": {"$exists": False},
        "device_id": {"$exists": True}
    })
    
    print(f"Found {total_files} files without user_id")
    
    if total_files == 0:
        print("No files need migration. All files already have user_id.")
        return
    
    updated_count = 0
    error_count = 0
    
    for file_doc in files_without_user_id:
        try:
            device_id = file_doc.get("device_id")
            if not device_id:
                print(f"Warning: File {file_doc.get('_id')} has no device_id, skipping")
                error_count += 1
                continue
            
            # Find the device to get the user_id
            device = device_collection.find_one({"_id": device_id})
            if not device:
                print(f"Warning: Device {device_id} not found for file {file_doc.get('_id')}")
                error_count += 1
                continue
            
            user_id = device.get("user_id")
            if not user_id:
                print(f"Warning: Device {device_id} has no user_id for file {file_doc.get('_id')}")
                error_count += 1
                continue
            
            # Update the file with user_id
            result = file_collection.update_one(
                {"_id": file_doc["_id"]},
                {"$set": {"user_id": user_id}}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"Updated {updated_count}/{total_files} files...")
            else:
                print(f"Warning: Failed to update file {file_doc.get('_id')}")
                error_count += 1
                
        except Exception as e:
            print(f"Error processing file {file_doc.get('_id')}: {str(e)}")
            error_count += 1
    
    print(f"\nMigration completed at {datetime.now()}")
    print(f"Successfully updated: {updated_count} files")
    print(f"Errors: {error_count} files")
    print(f"Total processed: {updated_count + error_count}/{total_files}")
    
    # Verify the migration
    remaining_files = file_collection.count_documents({
        "user_id": {"$exists": False},
        "device_id": {"$exists": True}
    })
    print(f"Files still without user_id: {remaining_files}")

if __name__ == "__main__":
    migrate_files_add_user_id()
