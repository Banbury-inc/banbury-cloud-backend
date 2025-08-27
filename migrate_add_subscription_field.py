#!/usr/bin/env python3
"""
Migration script to add subscription field to all users in the users collection.

This script will:
1. Add a 'subscription' field to all user documents
2. Set the default value to 'free'
3. Provide a summary of the migration
4. Optionally backup the users collection before migration

Usage:
    python migrate_add_subscription_field.py [--dry-run] [--backup]
"""

import sys
import argparse
from datetime import datetime
from pymongo import MongoClient

def connect_to_mongodb():
    """Connect to MongoDB and return database instance."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    return client["NeuraNet"]

def backup_users_collection(db, backup_suffix=None):
    """Create a backup of the users collection."""
    if not backup_suffix:
        backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_collection_name = f"users_backup_{backup_suffix}"
    
    try:
        # Use aggregation to copy all documents
        pipeline = [{"$match": {}}]
        users_docs = list(db["users"].aggregate(pipeline))
        
        if users_docs:
            db[backup_collection_name].insert_many(users_docs)
            print(f"✓ Backup created: {backup_collection_name} ({len(users_docs)} documents)")
        else:
            print("ℹ No documents to backup in users collection")
            
        return backup_collection_name
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return None

def migrate_subscription_field(db, dry_run=False):
    """Add subscription field to all users and set it to 'free'."""
    
    # Get all users that don't already have a subscription field
    users_without_subscription = list(db["users"].find({"subscription": {"$exists": False}}))
    
    if not users_without_subscription:
        print("ℹ All users already have subscription field")
        return {
            'total_users': 0,
            'updated': 0,
            'errors': 0,
            'errors_list': []
        }
    
    print(f"📊 Found {len(users_without_subscription)} users without subscription field")
    
    updated_count = 0
    error_count = 0
    errors_list = []
    
    for user in users_without_subscription:
        try:
            user_id = user.get('_id')
            username = user.get('username', 'unknown')
            
            if not dry_run:
                # Perform the actual update
                result = db["users"].update_one(
                    {"_id": user_id},
                    {"$set": {"subscription": "free"}}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    print(f"✓ Added subscription field for user: {username}")
                else:
                    error_msg = f"Failed to update user: {username}"
                    print(f"✗ {error_msg}")
                    error_count += 1
                    errors_list.append(error_msg)
            else:
                # Dry run - just show what would be updated
                print(f"🔍 Would add subscription field for user: {username}")
                updated_count += 1
                
        except Exception as e:
            error_msg = f"Error processing user {user.get('username', 'unknown')}: {str(e)}"
            print(f"✗ {error_msg}")
            error_count += 1
            errors_list.append(error_msg)
    
    return {
        'total_users': len(users_without_subscription),
        'updated': updated_count,
        'errors': error_count,
        'errors_list': errors_list
    }

def verify_migration(db):
    """Verify that the migration was successful."""
    print("\n🔍 Verifying migration...")
    
    # Check users with subscription field
    users_with_subscription = db["users"].find({"subscription": {"$exists": True}})
    users_with_subscription = list(users_with_subscription)
    
    print(f"✓ Found {len(users_with_subscription)} users with subscription field")
    
    # Count by subscription type
    subscription_counts = {}
    for user in users_with_subscription:
        subscription = user.get('subscription', 'unknown')
        subscription_counts[subscription] = subscription_counts.get(subscription, 0) + 1
    
    print("\n📋 Subscription breakdown:")
    for subscription, count in subscription_counts.items():
        print(f"  - {subscription}: {count} users")
    
    # Show some examples
    if users_with_subscription:
        print("\n📋 Sample users with subscription field:")
        for user in users_with_subscription[:5]:  # Show first 5
            username = user.get('username', 'unknown')
            subscription = user.get('subscription', 'unknown')
            print(f"  - {username}: {subscription}")

def main():
    parser = argparse.ArgumentParser(description='Add subscription field to users collection')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be migrated without making changes')
    parser.add_argument('--backup', action='store_true',
                       help='Create a backup of the users collection before migration')
    
    args = parser.parse_args()
    
    print("🚀 Starting Subscription Field Migration")
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
            backup_name = backup_users_collection(db)
        
        # Perform migration
        print("\n🔄 Starting migration...")
        migration_stats = migrate_subscription_field(db, dry_run=args.dry_run)
        
        # Print summary
        print("\n📊 Migration Summary")
        print("=" * 30)
        print(f"Total users to update: {migration_stats['total_users']}")
        print(f"Successfully updated: {migration_stats['updated']}")
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
        
        print("\n✅ Migration completed!")
        
        if backup_name:
            print(f"💾 Backup saved as: {backup_name}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
