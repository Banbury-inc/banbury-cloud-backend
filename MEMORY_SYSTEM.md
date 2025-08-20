# Enhanced Memory Management System

This document describes the enhanced memory management system implemented in the banbury-cloud-backend, which integrates Zep Cloud with the existing MongoDB-based memory system.

## Overview

The enhanced memory system provides both basic memory storage (MongoDB) and advanced semantic memory capabilities (Zep Cloud). This hybrid approach ensures backward compatibility while adding powerful new features like semantic search, knowledge graphs, and entity extraction.

## Architecture

### Components

1. **MongoDB Memory Storage** (`apps/conversations/models.py`)
   - Basic memory storage and retrieval
   - Session-based memory isolation
   - Simple keyword search

2. **Enhanced Memory Service** (`apps/conversations/memory_service.py`)
   - Zep Cloud integration
   - Hybrid storage and search
   - Entity recognition and knowledge graphs
   - Conversation context management

3. **API Endpoints** (`apps/conversations/views.py`)
   - Basic memory endpoints (MongoDB only)
   - Enhanced memory endpoints (Zep Cloud + MongoDB)
   - Status and health check endpoints

## Features

### Basic Memory (MongoDB)
- ✅ Simple memory storage and retrieval
- ✅ Session-based memory isolation
- ✅ Keyword-based search
- ✅ Memory cleanup and management

### Enhanced Memory (Zep Cloud)
- ✅ Semantic search with multiple rerankers
- ✅ Entity extraction (Person, Company)
- ✅ Knowledge graph with relationships
- ✅ Conversation context preservation
- ✅ Confidence scoring for search results

### Hybrid Features
- ✅ Automatic fallback to MongoDB if Zep fails
- ✅ Combined search results from both systems
- ✅ Configurable Zep usage per operation

## Setup

### Environment Variables

Add the following environment variables to your Django settings:

```bash
# Zep Cloud API Key (Required for enhanced features)
ZEP_API_KEY=your_zep_api_key_here

# Mem0 API Key (Optional for future features)
MEM0_API_KEY=your_mem0_api_key_here
```

### Dependencies

The required dependencies are already added to `requirements.txt`:

```
zep-cloud==2.8.0
mem0ai==0.1.32
```

## API Endpoints

### Basic Memory Endpoints

#### Store Memory
```bash
POST /conversations/memory/store/
{
    "content": "Memory content to store",
    "type": "memory_type" (optional),
    "session_id": "session_id" (optional),
    "metadata": {...} (optional)
}
```

#### Search Memories
```bash
GET /conversations/memory/search/?query=search_term&session_id=default&limit=10&type=general
```

#### Get Memories
```bash
GET /conversations/memory/list/?session_id=default&limit=50&offset=0&type=general
```

#### Delete Memory
```bash
DELETE /conversations/memory/{memory_id}/delete/
```

### Enhanced Memory Endpoints

#### Store Memory (Enhanced)
```bash
POST /conversations/memory/enhanced/store/
{
    "content": "Memory content to store",
    "type": "memory_type" (optional),
    "session_id": "session_id" (optional),
    "metadata": {...} (optional),
    "use_zep": true (optional, default: true)
}
```

#### Search Memories (Enhanced)
```bash
GET /conversations/memory/enhanced/search/?query=search_term&session_id=default&limit=10&use_zep=true&scope=nodes&reranker=cross_encoder
```

#### Get Memory Context
```bash
GET /conversations/memory/context/?session_id=session_id&limit=10
```

#### Add Conversation to Memory
```bash
POST /conversations/memory/conversation/
{
    "session_id": "session_id",
    "messages": [...]
}
```

#### Get Memory Status
```bash
GET /conversations/memory/status/
```

## Usage Examples

### Python Usage

```python
from apps.conversations.memory_service import memory_service
import asyncio

# Store memory with Zep Cloud
async def store_memory():
    result = await memory_service.store_memory_enhanced(
        username="user123",
        content="User prefers Python for data analysis",
        memory_type="preference",
        session_id="session_123",
        use_zep=True
    )
    print(result)

# Search memories with semantic search
async def search_memories():
    result = await memory_service.search_memories_enhanced(
        username="user123",
        query="Python preferences",
        session_id="session_123",
        limit=10,
        use_zep=True,
        scope="nodes",
        reranker="cross_encoder"
    )
    print(result)

# Get conversation context
async def get_context():
    context = await memory_service.get_memory_context(
        username="user123",
        session_id="session_123",
        limit=10
    )
    print(context)

# Run async functions
asyncio.run(store_memory())
asyncio.run(search_memories())
asyncio.run(get_context())
```

### Frontend Usage

```javascript
// Store memory
const storeResponse = await fetch('/conversations/memory/enhanced/store/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
        content: 'User prefers dark mode',
        type: 'preference',
        session_id: 'session_123',
        use_zep: true
    })
});

// Search memories
const searchResponse = await fetch('/conversations/memory/enhanced/search/?query=dark mode&use_zep=true&scope=nodes', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

// Get memory status
const statusResponse = await fetch('/conversations/memory/status/', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

## Configuration

### Memory Service Configuration

The memory service automatically detects available features based on environment variables:

```python
# Check if Zep Cloud is enabled
if memory_service.is_zep_enabled():
    print("Zep Cloud is available")
else:
    print("Zep Cloud is not configured")

# Get service status
status = memory_service.get_memory_status()
print(status)
```

### Search Parameters

#### Scope Options
- **nodes**: Search for entities and concepts
- **edges**: Search for relationships and facts

#### Reranker Options
- **cross_encoder**: High-accuracy transformer-based ranking
- **rrf**: Reciprocal Rank Fusion for robust results
- **mmr**: Maximal Marginal Relevance for diversity
- **episode_mentions**: Recurring topic prioritization

## Entity Types

### Person Entity
```python
{
    "name": "John Doe",
    "role": "Software Engineer",
    "company": "Tech Corp",
    "email": "john@techcorp.com",
    "phone": "+1-555-0123",
    "expertise": ["Python", "Machine Learning"]
}
```

### Company Entity
```python
{
    "name": "Tech Corp",
    "industry": "Technology",
    "size": "500-1000 employees",
    "website": "https://techcorp.com",
    "description": "Leading technology company"
}
```

## Error Handling

The system provides comprehensive error handling:

```python
try:
    result = await memory_service.store_memory_enhanced(...)
    if result["success"]:
        print("Memory stored successfully")
    else:
        print(f"Error: {result.get('error')}")
except Exception as e:
    print(f"Exception: {e}")
```

### Common Error Scenarios

1. **Zep Cloud not configured**
   - System falls back to MongoDB-only operations
   - No data loss, just reduced functionality

2. **Network issues**
   - Automatic retry logic
   - Graceful degradation to MongoDB

3. **Invalid data**
   - Input validation
   - Clear error messages

## Performance Considerations

### Memory Limits
- **MongoDB**: No strict limits
- **Zep Cloud**: 10,000 characters per memory
- **Search queries**: 255 characters max for Zep

### Caching
- Session-based caching for frequently accessed memories
- Result caching for search operations
- User profile caching

### Async Operations
- All Zep Cloud operations are async
- Non-blocking memory operations
- Concurrent search capabilities

## Monitoring

### Health Checks
```bash
GET /conversations/memory/status/
```

Response:
```json
{
    "success": true,
    "status": {
        "zep_enabled": true,
        "mem0_enabled": false,
        "mongo_enabled": true,
        "features": {
            "semantic_search": true,
            "knowledge_graph": true,
            "entity_extraction": true,
            "conversation_context": true,
            "basic_search": true,
            "basic_storage": true
        }
    }
}
```

### Metrics to Monitor
- Memory storage operations per user
- Search performance and response times
- Zep Cloud API usage and errors
- MongoDB operation success rates

## Troubleshooting

### Common Issues

1. **Zep Cloud not working**
   - Check `ZEP_API_KEY` environment variable
   - Verify network connectivity to Zep Cloud
   - Check Zep Cloud service status

2. **Search returns no results**
   - Verify user has stored memories
   - Check search query relevance
   - Adjust search scope or reranker

3. **Memory storage fails**
   - Check MongoDB connection
   - Verify user authentication
   - Check memory content size

### Debug Mode

Enable debug logging in Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps.conversations.memory_service': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Future Enhancements

### Planned Features
- **Multi-modal Memory**: Support for images and documents
- **Memory Analytics**: Usage insights and optimization
- **Advanced Search**: Natural language query processing
- **Memory Sharing**: Controlled sharing between users
- **Memory Export**: Data export and backup capabilities

### Integration Opportunities
- **Calendar Integration**: Meeting and event memory
- **Email Integration**: Communication history
- **Document Integration**: File content memory
- **Workflow Integration**: Process and task memory

## Migration Guide

### From Basic to Enhanced Memory

1. **Add environment variables**
   ```bash
   export ZEP_API_KEY=your_zep_api_key
   ```

2. **Update API calls**
   - Use enhanced endpoints for new features
   - Keep basic endpoints for backward compatibility

3. **Test functionality**
   - Verify Zep Cloud integration
   - Test semantic search capabilities
   - Validate entity extraction

### Backward Compatibility

- All existing basic memory endpoints continue to work
- No data migration required
- Gradual adoption of enhanced features

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review API documentation
3. Check Zep Cloud documentation
4. Contact the development team

---

This enhanced memory management system provides a robust foundation for AI assistants to maintain context and provide personalized experiences across conversations and sessions, while maintaining full backward compatibility with existing systems.
