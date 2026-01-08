#!/usr/bin/env python3
"""
Script to kill all MongoDB connections in the application.
This will close connections from the MongoDB manager and any other direct connections.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def kill_all_mongodb_connections():
    """Kill all MongoDB connections."""
    print("=" * 60)
    print("Killing all MongoDB connections...")
    print("=" * 60)
    
    connection_count = 0
    
    # 1. Close the main MongoDB manager connection
    print("\n[1] Closing MongoDB Manager connections...")
    try:
        from core.mongodb_manager import mongodb_manager
        
        # Check if connection exists
        if mongodb_manager._client is not None:
            print(f"   Found active MongoDB manager client")
            connection_count += 1
            
        # Close the connection
        mongodb_manager.close_connection()
        print("   ✓ MongoDB Manager connections closed")
    except Exception as e:
        print(f"   ✗ Error closing MongoDB Manager: {e}")
    
    # 2. Close meeting agent MongoDB connections
    print("\n[2] Closing Meeting Agent MongoDB connections...")
    try:
        from apps.meeting_agent import mongodb_models
        
        # The meeting_agent creates connections on-demand, so we need to check
        # if any manager instances exist and close their underlying clients
        managers = [
            ('meeting_platforms', mongodb_models.meeting_platforms),
            ('meeting_sessions', mongodb_models.meeting_sessions),
            ('meeting_configs', mongodb_models.meeting_configs),
            ('meeting_status', mongodb_models.meeting_status),
        ]
        
        for manager_name, manager in managers:
            try:
                if hasattr(manager, 'db') and hasattr(manager.db, 'client'):
                    print(f"   Found active connection in {manager_name}")
                    manager.db.client.close()
                    connection_count += 1
                    print(f"   ✓ Closed connection in {manager_name}")
            except Exception as e:
                print(f"   ✗ Error closing {manager_name}: {e}")
        
        print("   ✓ Meeting Agent connections processed")
    except Exception as e:
        print(f"   ✗ Error processing Meeting Agent connections: {e}")
    
    # 3. Force garbage collection to clean up any remaining connections
    print("\n[3] Running garbage collection...")
    try:
        import gc
        gc.collect()
        print("   ✓ Garbage collection complete")
    except Exception as e:
        print(f"   ✗ Error running garbage collection: {e}")
    
    # 4. Summary
    print("\n" + "=" * 60)
    print(f"Summary: Processed {connection_count} MongoDB connection(s)")
    print("All MongoDB connection cleanup attempts complete")
    print("=" * 60)

if __name__ == "__main__":
    try:
        kill_all_mongodb_connections()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
