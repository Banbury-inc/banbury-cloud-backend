# Conversations App - Memory API

This app now includes AI memory management functionality that allows storing and retrieving contextual information for AI assistants.

## Memory Endpoints

### Store Memory
**POST** `/conversations/memory/store/`

Store a new memory in the database.

**Request Body:**
```json
{
  "content": "Memory content to store",
  "type": "memory_type" (optional, default: "general"),
  "session_id": "session_id" (optional, default: "default"),
  "metadata": {...} (optional)
}
```

**Response:**
```json
{
  "success": true,
  "memory_id": "memory_id",
  "message": "Memory stored successfully"
}
```

### Search Memories
**GET** `/conversations/memory/search/`

Search memories for relevant information.

**Query Parameters:**
- `query` (required): Search query
- `session_id` (optional): Session ID for memory isolation (default: "default")
- `limit` (optional): Maximum number of memories to return (default: 10)
- `type` (optional): Filter by memory type

**Response:**
```json
{
  "success": true,
  "memories": [
    {
      "_id": "memory_id",
      "content": "Memory content",
      "type": "memory_type",
      "session_id": "session_id",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### List Memories
**GET** `/conversations/memory/list/`

Get all memories for a user.

**Query Parameters:**
- `session_id` (optional): Session ID for memory isolation (default: "default")
- `limit` (optional): Maximum number of memories to return (default: 50)
- `offset` (optional): Number of memories to skip (default: 0)
- `type` (optional): Filter by memory type

### Delete Memory
**DELETE** `/conversations/memory/{memory_id}/delete/`

Delete a specific memory by ID.

### Delete Memories by Session
**DELETE** `/conversations/memory/delete-session/`

Delete all memories for a specific session.

**Request Body:**
```json
{
  "session_id": "session_id"
}
```

### Cleanup Old Memories
**POST** `/conversations/memory/cleanup/`

Clean up old memories for the authenticated user.

**Request Body:**
```json
{
  "days_to_keep": 30 (optional, default: 30)
}
```

## Database Schema

Memories are stored in the `memories` collection in MongoDB with the following structure:

```json
{
  "_id": "ObjectId",
  "username": "string",
  "content": "string",
  "type": "string",
  "session_id": "string",
  "metadata": "object",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Frontend Integration

The frontend memory tools in `Banbury-Website/frontend/src/lib/langraph/agent.ts` have been updated to use these API endpoints instead of in-memory storage. The tools now:

1. **store_memory**: Stores memories via POST to `/conversations/memory/store/`
2. **search_memory**: Searches memories via GET to `/conversations/memory/search/`

Both tools use the authentication token from the server context to authenticate requests.

## Usage Examples

### Storing a Memory
```typescript
// Frontend tool call
await createMemoryTool.invoke({
  content: "User prefers dark mode interface",
  type: "preference",
  sessionId: "user_session_123"
});
```

### Searching Memories
```typescript
// Frontend tool call
await searchMemoryTool.invoke({
  query: "dark mode",
  sessionId: "user_session_123",
  limit: 5
});
```

## Security

- All endpoints require authentication via JWT token
- Memories are isolated by username
- Session-based isolation is supported for multi-session scenarios
- Automatic cleanup of old memories helps manage storage
