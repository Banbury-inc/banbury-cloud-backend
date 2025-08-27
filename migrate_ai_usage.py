#!/usr/bin/env python3
"""
Migration script to move AI usage data from ai_usage collection to user collection.

This script will:
1. Read all documents from the ai_usage collection
2. Update corresponding user documents with AI usage data
3. Provide a summary of the migration
4. Optionally backup the original ai_usage collection

Usage:
    python migrate_ai_usage.py [--dry-run] [--backup]
"""

import sys
import argparse
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

def connect_to_mongodb():
    """Connect to MongoDB and return database instance."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    return client["NeuraNet"]

def backup_ai_usage_collection(db, backup_suffix=None):
    """Create a backup of the ai_usage collection."""
    if not backup_suffix:
        backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_collection_name = f"ai_usage_backup_{backup_suffix}"
    
    try:
        # Use aggregation to copy all documents
        pipeline = [{"$match": {}}]
        ai_usage_docs = list(db["ai_usage"].aggregate(pipeline))
        
        if ai_usage_docs:
            db[backup_collection_name].insert_many(ai_usage_docs)
            print(f"✓ Backup created: {backup_collection_name} ({len(ai_usage_docs)} documents)")
        else:
            print("ℹ No documents to backup in ai_usage collection")
            
        return backup_collection_name
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return None

def migrate_ai_usage_data(db, dry_run=False):
    """Migrate AI usage data from ai_usage collection to user collection."""
    
    # Get all AI usage documents
    ai_usage_docs = list(db["ai_usage"].find({}))
    
    if not ai_usage_docs:
        print("ℹ No AI usage data found to migrate")
        return {
            'total_docs': 0,
            'migrated': 0,
            'errors': 0,
            'errors_list': []
        }
    
    print(f"📊 Found {len(ai_usage_docs)} AI usage documents to migrate")
    
    migrated_count = 0
    error_count = 0
    errors_list = []
    
    for doc in ai_usage_docs:
        try:
            user_id = doc.get('user_id')
            message_count = doc.get('message_count', 0)
            last_message_at = doc.get('last_message_at')
            created_at = doc.get('created_at')
            
            # Find the corresponding user
            user = db["users"].find_one({"_id": user_id})
            
            if not user:
                error_msg = f"User not found for user_id: {user_id}"
                print(f"⚠ {error_msg}")
                error_count += 1
                errors_list.append(error_msg)
                continue
            
            username = user.get('username', 'unknown')
            
            # Prepare update data
            update_data = {
                "$set": {
                    "ai_message_count": message_count,
                    "last_ai_message_at": last_message_at
                }
            }
            
            # Only set created_at if it doesn't already exist
            if created_at:
                update_data["$setOnInsert"] = {
                    "ai_usage_created_at": created_at
                }
            
            if not dry_run:
                # Perform the actual update
                result = db["users"].update_one(
                    {"_id": user_id},
                    update_data
                )
                
                if result.modified_count > 0 or result.matched_count > 0:
                    migrated_count += 1
                    print(f"✓ Migrated AI usage for user: {username} (count: {message_count})")
                else:
                    error_msg = f"Failed to update user: {username}"
                    print(f"✗ {error_msg}")
                    error_count += 1
                    errors_list.append(error_msg)
            else:
                # Dry run - just show what would be updated
                print(f"🔍 Would migrate AI usage for user: {username} (count: {message_count})")
                migrated_count += 1
                
        except Exception as e:
            error_msg = f"Error processing document {doc.get('_id')}: {str(e)}"
            print(f"✗ {error_msg}")
            error_count += 1
            errors_list.append(error_msg)
    
    return {
        'total_docs': len(ai_usage_docs),
        'migrated': migrated_count,
        'errors': error_count,
        'errors_list': errors_list
    }

def verify_migration(db):
    """Verify that the migration was successful."""
    print("\n🔍 Verifying migration...")
    
    # Check users with AI usage data
    users_with_ai_usage = db["users"].find({"ai_message_count": {"$exists": True, "$gt": 0}})
    users_with_ai_usage = list(users_with_ai_usage)
    
    print(f"✓ Found {len(users_with_ai_usage)} users with AI usage data")
    
    # Show some examples
    if users_with_ai_usage:
        print("\n📋 Sample migrated users:")
        for user in users_with_ai_usage[:5]:  # Show first 5
            username = user.get('username', 'unknown')
            count = user.get('ai_message_count', 0)
            last_message = user.get('last_ai_message_at', 'N/A')
            print(f"  - {username}: {count} messages, last: {last_message}")
    
    # Check if any users have both old and new format (shouldn't happen)
    users_with_both = db["users"].find({
        "ai_message_count": {"$exists": True},
        "$or": [
            {"message_count": {"$exists": True}},
            {"last_message_at": {"$exists": True}}
        ]
    })
    users_with_both = list(users_with_both)
    
    if users_with_both:
        print(f"⚠ Warning: {len(users_with_both)} users have both old and new AI usage fields")
    else:
        print("✓ No conflicts found between old and new AI usage fields")

def cleanup_old_collection(db, dry_run=False):
    """Remove the old ai_usage collection after successful migration."""
    try:
        if not dry_run:
            db["ai_usage"].drop()
            print("✓ Dropped old ai_usage collection")
        else:
            print("🔍 Would drop old ai_usage collection (dry run)")
        return True
    except Exception as e:
        print(f"✗ Error dropping ai_usage collection: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate AI usage data to user collection')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be migrated without making changes')
    parser.add_argument('--backup', action='store_true',
                       help='Create a backup of the ai_usage collection before migration')
    parser.add_argument('--cleanup', action='store_true',
                       help='Remove the old ai_usage collection after migration')
    
    args = parser.parse_args()
    
    print("🚀 Starting AI Usage Migration")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        print("✓ Connected to MongoDB")
        
        # Create backup if requested
        backup_name = None
        if args.backup and not args.dry_run:
            print("\n📦 Creating backup...")
            backup_name = backup_ai_usage_collection(db)
        
        # Perform migration
        print("\n🔄 Starting migration...")
        migration_stats = migrate_ai_usage_data(db, dry_run=args.dry_run)
        
        # Print summary
        print("\n📊 Migration Summary")
        print("=" * 30)
        print(f"Total documents: {migration_stats['total_docs']}")
        print(f"Successfully migrated: {migration_stats['migrated']}")
        print(f"Errors: {migration_stats['errors']}")
        
        if migration_stats['errors'] > 0:
            print("\n❌ Errors encountered:")
            for error in migration_stats['errors_list'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(migration_stats['errors_list']) > 5:
                print(f"  ... and {len(migration_stats['errors_list']) - 5} more")
        
        # Verify migration
        if not args.dry_run and migration_stats['errors'] == 0:
            verify_migration(db)
        
        # Cleanup old collection
        if args.cleanup and not args.dry_run and migration_stats['errors'] == 0:
            print("\n🧹 Cleaning up old collection...")
            cleanup_old_collection(db, dry_run=args.dry_run)
        
        print("\n✅ Migration completed!")
        
        if backup_name:
            print(f"💾 Backup saved as: {backup_name}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
