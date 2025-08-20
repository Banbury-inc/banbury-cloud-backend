from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from .models import Conversation, Memory
from .memory_service import memory_service

@csrf_exempt
@require_http_methods(["POST"])
def save_conversation(request):
    """
    Save a conversation to the database
    
    Expected JSON payload:
    {
        "title": "Conversation title",
        "messages": [...],
        "metadata": {...} (optional)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        title = data.get("title")
        messages = data.get("messages", [])
        metadata = data.get("metadata")
        
        if not title:
            return JsonResponse({
                "success": False,
                "error": "Title is required"
            }, status=400)
        
        if not messages:
            return JsonResponse({
                "success": False,
                "error": "Messages are required"
            }, status=400)
        
        result = Conversation.save_conversation(username, title, messages, metadata)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_conversations(request):
    """
    Get conversations for the authenticated user
    
    Query parameters:
    - limit: Maximum number of conversations to return (default: 50)
    - offset: Number of conversations to skip (default: 0)
    """
    try:
        username = request.username_from_token
        
        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        
        result = Conversation.get_conversations(username, limit, offset)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid limit or offset parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_conversation(request, conversation_id):
    """
    Get a specific conversation by ID
    """
    try:
        username = request.username_from_token
        
        result = Conversation.get_conversation(conversation_id, username)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
def update_conversation_title(request, conversation_id):
    """
    Update the title of a conversation
    
    Expected JSON payload:
    {
        "title": "New conversation title"
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        title = data.get("title")
        if not title:
            return JsonResponse({
                "success": False,
                "error": "Title is required"
            }, status=400)
        
        result = Conversation.update_conversation_title(conversation_id, username, title)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
def update_conversation(request, conversation_id):
    """
    Update an entire conversation
    
    Expected JSON payload:
    {
        "title": "Conversation title",
        "messages": [...],
        "metadata": {...} (optional)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        title = data.get("title")
        messages = data.get("messages", [])
        metadata = data.get("metadata")
        
        if not title:
            return JsonResponse({
                "success": False,
                "error": "Title is required"
            }, status=400)
        
        if not messages:
            return JsonResponse({
                "success": False,
                "error": "Messages are required"
            }, status=400)
        
        result = Conversation.update_conversation(conversation_id, username, title, messages, metadata)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_conversation(request, conversation_id):
    """
    Delete a conversation by ID
    """
    try:
        username = request.username_from_token
        
        result = Conversation.delete_conversation(conversation_id, username)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def store_memory(request):
    """
    Store a memory in the database
    
    Expected JSON payload:
    {
        "content": "Memory content to store",
        "type": "memory_type" (optional),
        "session_id": "session_id" (optional),
        "metadata": {...} (optional)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        content = data.get("content")
        memory_type = data.get("type", "general")
        session_id = data.get("session_id", "default")
        metadata = data.get("metadata")
        
        if not content:
            return JsonResponse({
                "success": False,
                "error": "Content is required"
            }, status=400)
        
        result = Memory.store_memory(username, content, memory_type, session_id, metadata)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def search_memories(request):
    """
    Search memories for the authenticated user
    
    Query parameters:
    - query: Search query (required)
    - session_id: Session ID for memory isolation (default: "default")
    - limit: Maximum number of memories to return (default: 10)
    - type: Filter by memory type (optional)
    """
    try:
        username = request.username_from_token
        
        query = request.GET.get("query")
        if not query:
            return JsonResponse({
                "success": False,
                "error": "Query parameter is required"
            }, status=400)
        
        session_id = request.GET.get("session_id", "default")
        limit = int(request.GET.get("limit", 10))
        memory_type = request.GET.get("type")
        
        result = Memory.search_memories(username, query, session_id, limit, memory_type)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid limit parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_memories(request):
    """
    Get memories for the authenticated user
    
    Query parameters:
    - session_id: Session ID for memory isolation (default: "default")
    - limit: Maximum number of memories to return (default: 50)
    - offset: Number of memories to skip (default: 0)
    - type: Filter by memory type (optional)
    """
    try:
        username = request.username_from_token
        
        session_id = request.GET.get("session_id", "default")
        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        memory_type = request.GET.get("type")
        
        result = Memory.get_memories(username, session_id, limit, offset, memory_type)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid limit or offset parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_memory(request, memory_id):
    """
    Delete a specific memory by ID
    """
    try:
        username = request.username_from_token
        
        result = Memory.delete_memory(memory_id, username)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_memories_by_session(request):
    """
    Delete all memories for a specific session
    
    Expected JSON payload:
    {
        "session_id": "session_id"
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        session_id = data.get("session_id")
        if not session_id:
            return JsonResponse({
                "success": False,
                "error": "Session ID is required"
            }, status=400)
        
        result = Memory.delete_memories_by_session(username, session_id)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def cleanup_old_memories(request):
    """
    Clean up old memories for the authenticated user
    
    Expected JSON payload:
    {
        "days_to_keep": 30 (optional, default: 30)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        days_to_keep = data.get("days_to_keep", 30)
        
        result = Memory.cleanup_old_memories(username, days_to_keep)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

# Enhanced Memory Endpoints with Zep Cloud Integration

@csrf_exempt
@require_http_methods(["POST"])
def store_memory_enhanced(request):
    """
    Store memory with enhanced Zep Cloud integration
    
    Expected JSON payload:
    {
        "content": "Memory content to store",
        "type": "memory_type" (optional),
        "session_id": "session_id" (optional),
        "metadata": {...} (optional),
        "use_zep": true (optional, default: true)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        content = data.get("content")
        memory_type = data.get("type", "general")
        session_id = data.get("session_id", "default")
        metadata = data.get("metadata")
        use_zep = data.get("use_zep", True)
        
        if not content:
            return JsonResponse({
                "success": False,
                "error": "Content is required"
            }, status=400)
        
        # Call synchronous function
        result = memory_service.store_memory_enhanced(
            username, content, memory_type, session_id, metadata, use_zep
        )
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def search_memories_enhanced(request):
    """
    Search memories with enhanced Zep Cloud integration
    
    Query parameters:
    - query: Search query (required)
    - session_id: Session ID for memory isolation (default: "default")
    - limit: Maximum number of memories to return (default: 10)
    - type: Filter by memory type (optional)
    - use_zep: Use Zep Cloud (optional, default: true)
    - scope: Search scope for Zep (optional, default: "nodes")
    - reranker: Reranker method for Zep (optional, default: "cross_encoder")
    """
    try:
        username = request.username_from_token
        
        query = request.GET.get("query")
        if not query:
            return JsonResponse({
                "success": False,
                "error": "Query parameter is required"
            }, status=400)
        
        session_id = request.GET.get("session_id", "default")
        limit = int(request.GET.get("limit", 10))
        memory_type = request.GET.get("type")
        use_zep = request.GET.get("use_zep", "true").lower() == "true"
        scope = request.GET.get("scope", "nodes")
        reranker = request.GET.get("reranker", "cross_encoder")
        
        # Call synchronous function
        result = memory_service.search_memories_enhanced(
            username, query, session_id, limit, memory_type, use_zep, scope, reranker
        )
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid limit parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_memory_context(request):
    """
    Get memory context for a conversation
    
    Query parameters:
    - session_id: Session ID (required)
    - limit: Maximum number of messages to return (default: 10)
    """
    try:
        username = request.username_from_token
        
        session_id = request.GET.get("session_id")
        if not session_id:
            return JsonResponse({
                "success": False,
                "error": "Session ID is required"
            }, status=400)
        
        limit = int(request.GET.get("limit", 10))
        
        # Call synchronous function
        context = memory_service.get_memory_context(username, session_id, limit=limit)
        
        if context:
            return JsonResponse({
                "success": True,
                "context": context,
                "session_id": session_id
            })
        else:
            return JsonResponse({
                "success": False,
                "message": "No context found for this session"
            })
            
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid limit parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def add_conversation_to_memory(request):
    """
    Add a conversation to Zep memory
    
    Expected JSON payload:
    {
        "session_id": "session_id" (required),
        "messages": [...] (required)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        session_id = data.get("session_id")
        messages = data.get("messages", [])
        
        if not session_id:
            return JsonResponse({
                "success": False,
                "error": "Session ID is required"
            }, status=400)
        
        if not messages:
            return JsonResponse({
                "success": False,
                "error": "Messages are required"
            }, status=400)
        
        # Call synchronous function
        result = memory_service.add_conversation_to_memory(username, session_id, messages)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_memory_status(request):
    """
    Get memory service status and capabilities
    """
    try:
        status = memory_service.get_memory_status()
        return JsonResponse({
            "success": True,
            "status": status
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
