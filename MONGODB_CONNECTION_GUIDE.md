# MongoDB Connection Management Guide

## Overview

This guide outlines the implementation of centralized MongoDB connection management to solve the issue of too many connections and ensure proper connection pooling and cleanup.

## Problem Statement

Previously, the codebase had multiple issues:
- Each file created its own `MongoClient` instance
- No connection pooling or reuse
- Hardcoded MongoDB URIs across multiple files
- No proper connection cleanup
- Potential for connection leaks and database performance issues

## Solution Implemented

### 1. Centralized MongoDB Manager (`core/mongodb_manager.py`)

A singleton pattern MongoDB connection manager that:
- Ensures only one connection instance per application
- Implements proper connection pooling with optimized settings
- Provides convenient methods for accessing databases and collections
- Includes health checking and connection monitoring
- Handles graceful connection cleanup

**Key features:**
- **Connection Pooling**: maxPoolSize=50, minPoolSize=5
- **Timeouts**: Proper socket, connection, and server selection timeouts
- **Thread-safe**: Uses threading locks for singleton implementation
- **Lazy Initialization**: Connections are created only when needed

### 2. Refactored Files

The following files have been updated to use the centralized manager:

#### Backend Python Files:
- `apps/conversations/models.py` - Conversation and memory collections
- `apps/authentication/utils.py` - API keys collection
- `apps/devices/declare_user_online.py` - User status management
- `apps/devices/declare_user_offline.py` - User status management
- `apps/devices/declare_device_online.py` - Device status management
- `apps/settings/get_settings.py` - User settings management
- `apps/files/download_file.py` - File operations

#### Frontend TypeScript Files:
- `frontend/src/handlers/getNeuraNetData.ts` - Data retrieval with singleton pattern

### 3. Django Integration (`core/apps.py`)

Added proper Django integration with:
- Signal handlers for graceful shutdown (SIGTERM, SIGINT)
- Process exit cleanup handlers
- Request-level connection monitoring

### 4. Management Commands

Added `mongodb_health` management command for:
- Connection health checks
- Connection information display
- Manual connection cleanup

## Usage

### Basic Usage

```python
from core.mongodb_manager import get_mongodb_collection, get_mongodb_database

# Get a collection (recommended)
users_collection = get_mongodb_collection('users')
user = users_collection.find_one({'username': 'example'})

# Get a database
db = get_mongodb_database('NeuraNet')
collection = db['users']

# Health check
from core.mongodb_manager import mongodb_health_check
is_healthy = mongodb_health_check()
```

### Management Commands

```bash
# Check MongoDB connection health
python manage.py mongodb_health

# Get detailed connection information
python manage.py mongodb_health --info

# Close connections after health check
python manage.py mongodb_health --close
```

### Frontend Usage

```typescript
import { getTotalDataProcessed, closeMongoDBConnection } from './handlers/getNeuraNetData';

// Use the functions normally - connection pooling is handled automatically
const totalData = await getTotalDataProcessed();

// Close connections on application shutdown
await closeMongoDBConnection();
```

## Configuration

### Environment Variables

Set the MongoDB URI via environment variable (optional):
```bash
export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
```

If not set, it defaults to the current connection string.

### Connection Pool Settings

Current optimized settings in `mongodb_manager.py`:
- **maxPoolSize**: 50 connections
- **minPoolSize**: 5 connections
- **maxIdleTimeMS**: 30 seconds
- **waitQueueTimeoutMS**: 5 seconds
- **serverSelectionTimeoutMS**: 5 seconds
- **socketTimeoutMS**: 20 seconds
- **connectTimeoutMS**: 20 seconds

## Benefits

1. **Reduced Connection Overhead**: Single connection pool shared across the application
2. **Better Performance**: Connection reuse eliminates connection setup overhead
3. **Resource Management**: Proper connection limits prevent database overload
4. **Error Handling**: Centralized error handling and retry logic
5. **Monitoring**: Built-in health checks and connection monitoring
6. **Maintenance**: Single point of configuration for all MongoDB operations

## Migration Guide

### For New Code

```python
# OLD - Don't do this
from pymongo import MongoClient
client = MongoClient("mongodb://...")
db = client['NeuraNet']
collection = db['users']

# NEW - Use this instead
from core.mongodb_manager import get_mongodb_collection
collection = get_mongodb_collection('users')
```

### For Existing Code

Replace all `MongoClient` instantiations with the centralized manager:

1. Remove `pymongo.MongoClient` imports
2. Remove hardcoded URI strings
3. Replace connection creation with `get_mongodb_collection()` calls
4. Remove manual connection cleanup (handled automatically)

## Troubleshooting

### Health Check Issues

```bash
# Check if MongoDB is accessible
python manage.py mongodb_health

# If unhealthy, check:
# 1. Network connectivity
# 2. MongoDB URI correctness
# 3. Authentication credentials
# 4. Firewall settings
```

### Connection Pool Exhaustion

If you encounter connection pool exhaustion:

1. Check for connection leaks in your code
2. Increase `maxPoolSize` in `mongodb_manager.py`
3. Review `maxIdleTimeMS` settings
4. Monitor connection usage patterns

### Performance Issues

1. Use connection info to monitor pool usage:
   ```bash
   python manage.py mongodb_health --info
   ```

2. Adjust pool settings based on your application's needs
3. Consider implementing connection pooling metrics

## Best Practices

1. **Always use the centralized manager**: Never create direct `MongoClient` instances
2. **Don't store collections globally**: Get collections when needed to ensure fresh connections
3. **Handle exceptions**: Wrap database operations in try-catch blocks
4. **Monitor health**: Regularly check connection health in production
5. **Use indexes**: Ensure proper database indexing for performance
6. **Connection cleanup**: The manager handles cleanup automatically, but you can manually close if needed

## Implementation Notes

- The singleton pattern ensures thread-safety across Django workers
- Connection pooling settings are optimized for typical web application usage
- The manager automatically handles connection recovery and retries
- All existing functionality remains the same - only the connection mechanism changed

This implementation resolves the MongoDB connection issues while maintaining backward compatibility and improving overall application performance.
