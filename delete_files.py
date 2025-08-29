#!/usr/bin/env python3
"""
Script to delete all files from the files collection where original_device is "michael-mills-ubuntu"

This script connects to the MongoDB database and removes all file documents
that have the original_device field set to "michael-mills-ubuntu".

Usage:
    python delete_michael_mills_ubuntu_files.py

Safety Features:
    - Shows count of files to be deleted before proceeding
    - Requires user confirmation before deletion
    - Provides detailed output of the deletion process
"""

from pymongo import MongoClient
import sys


def delete_files_by_original_device(device_name):
    """
    Delete all files from the files collection where original_device matches the specified device name.
    
    Args:
        device_name (str): The original_device value to match for deletion
        
    Returns:
        dict: Result containing success status, count of deleted files, and any error messages
    """
    try:
        # MongoDB connection (using the same URI pattern as the codebase)
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        file_collection = db["files"]
        
        # First, count how many files match the criteria
        count = file_collection.count_documents({"original_device": device_name})
        
        if count == 0:
            return {
                "success": True,
                "deleted_count": 0,
                "message": f"No files found with original_device: {device_name}"
            }
        
        # Show the files that will be deleted (for verification)
        print(f"\nFound {count} files with original_device: {device_name}")
        print("\nSample files to be deleted:")
        sample_files = list(file_collection.find(
            {"original_device": device_name},
            {"file_name": 1, "file_path": 1, "file_size": 1, "date_uploaded": 1}
        ).limit(5))
        
        for i, file in enumerate(sample_files, 1):
            print(f"  {i}. {file.get('file_name', 'N/A')} - {file.get('file_path', 'N/A')} ({file.get('file_size', 0)} bytes)")
        
        if count > 5:
            print(f"  ... and {count - 5} more files")
        
        # Ask for confirmation
        print(f"\nAre you sure you want to delete ALL {count} files with original_device: {device_name}?")
        confirmation = input("Type 'YES' to confirm deletion: ")
        
        if confirmation != "YES":
            return {
                "success": False,
                "deleted_count": 0,
                "message": "Deletion cancelled by user"
            }
        
        # Perform the deletion
        result = file_collection.delete_many({"original_device": device_name})
        
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "message": f"Successfully deleted {result.deleted_count} files with original_device: {device_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "deleted_count": 0,
            "message": f"Error during deletion: {str(e)}"
        }
    finally:
        # Close the MongoDB connection
        if 'client' in locals():
            client.close()


def main():
    """Main function to execute the file deletion script."""
    device_name = "fv-az1778-662"
    
    print("=" * 60)
    print("FILE DELETION SCRIPT")
    print("=" * 60)
    print(f"Target device: {device_name}")
    print("Database: NeuraNet")
    print("Collection: files")
    print("=" * 60)
    
    # Execute the deletion
    result = delete_files_by_original_device(device_name)
    
    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if result["success"]:
        print(f"✅ {result['message']}")
        if result["deleted_count"] > 0:
            print(f"📊 Total files deleted: {result['deleted_count']}")
    else:
        print(f"❌ {result['message']}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
