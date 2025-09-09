#!/usr/bin/env python3
"""
Simple script to check if MongoDB is running
"""
import os
import sys
from pymongo import MongoClient

def check_mongodb():
    """Check if MongoDB is accessible"""
    try:
        # Try to connect to MongoDB
        host = os.environ.get('MONGODB_HOST', 'localhost')
        port = int(os.environ.get('MONGODB_PORT', 27017))
        
        client = MongoClient(host, port, serverSelectionTimeoutMS=3000)
        
        # Test the connection
        client.admin.command('ping')
        
        print("✅ MongoDB is running and accessible")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        
        # List databases
        dbs = client.list_database_names()
        print(f"   Databases: {', '.join(dbs)}")
        
        return True
        
    except Exception as e:
        print("❌ MongoDB is not accessible")
        print(f"   Error: {e}")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print("\n💡 To start MongoDB:")
        print("   - Using Docker: docker run -d -p 27017:27017 --name mongodb mongo:latest")
        print("   - Or install MongoDB locally and start the service")
        
        return False

if __name__ == "__main__":
    success = check_mongodb()
    sys.exit(0 if success else 1)
