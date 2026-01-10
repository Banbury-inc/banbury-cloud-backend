from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from .models import Conversation, Memory
from .memory_service import memory_service
from datetime import datetime

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
def get_all_conversations_admin(request):
    """
    Get all conversations across all users for admin analytics

    Query parameters:
    - limit: Maximum number of conversations to return (default: 50)
    - offset: Number of conversations to skip (default: 0)
    - days: Number of days to look back (default: 30)
    - username: Filter by specific username (optional)
    """
    try:
        username = request.username_from_token

        # Admin check - only allow mmills and mmills6060@gmail.com
        if username not in ['mmills', 'mmills6060@gmail.com']:
            return JsonResponse({
                "success": False,
                "error": "Unauthorized - Admin access required"
            }, status=403)

        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        days = int(request.GET.get("days", 30))
        user_filter = request.GET.get("username", "")

        result = Conversation.get_all_conversations_admin(limit, offset, days, user_filter)

        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)

    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid limit, offset, or days parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_conversation_users_admin(request):
    """
    Get list of users who have conversations for admin analytics

    Query parameters:
    - days: Number of days to look back (default: 30)
    """
    try:
        username = request.username_from_token

        # Admin check - only allow mmills and mmills6060@gmail.com
        if username not in ['mmills', 'mmills6060@gmail.com']:
            return JsonResponse({
                "success": False,
                "error": "Unauthorized - Admin access required"
            }, status=403)

        days = int(request.GET.get("days", 30))

        result = Conversation.get_conversation_users_admin(days)

        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)

    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Invalid days parameter"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_conversation_admin(request, conversation_id):
    """
    Get a specific conversation by ID for admin (no username check)
    """
    try:
        username = request.username_from_token

        # Admin check - only allow mmills and mmills6060@gmail.com
        if username not in ['mmills', 'mmills6060@gmail.com']:
            return JsonResponse({
                "success": False,
                "error": "Unauthorized - Admin access required"
            }, status=403)
        
        result = Conversation.get_conversation_admin(conversation_id)
        
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
@require_http_methods(["DELETE"])
def delete_all_conversations(request):
    """
    Delete all conversations for the authenticated user
    """
    try:
        username = request.username_from_token
        
        result = Conversation.delete_all_conversations(username)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
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

# Knowledge Graph Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def get_knowledge_graph(request):
    """
    Get the full knowledge graph data for the authenticated user
    
    Query parameters:
    - limit: Maximum number of entities/facts to return (default: 50)
    - scope: Search scope - 'nodes' for entities, 'edges' for facts, or 'both' (default: 'both')
    """
    try:
        username = request.username_from_token
        
        limit = int(request.GET.get("limit", 50))
        scope = request.GET.get("scope", "both")
        
        if scope == "both":
            # Use rich search results for entities
            entities_result = memory_service.search_memories_enhanced(
                username, "", "assistant_ui", limit, None, True, "nodes", "cross_encoder"
            )
            
            # Try to get rich facts from search first, fallback to thread messages
            try:
                facts_result = memory_service.search_memories_enhanced(
                    username, "user", "assistant_ui", limit, None, True, "edges", "cross_encoder"
                )
                if not facts_result.get("zep_facts"):
                    raise Exception("No facts found in search")
            except:
                # Fallback to thread messages
                all_messages = memory_service.get_thread_messages(username, "assistant_ui", limit)
                facts = []
                for msg in all_messages:
                    facts.append({
                        "fact": f"{msg.get('role', 'user')}: {msg.get('content', '')}",
                        "confidence": 1.0,
                        "score": 1.0,
                        "created_at": msg.get('created_at', ''),
                        "uuid": msg.get('uuid', ''),
                        "labels": [msg.get('role', 'user'), "message"],
                        "attributes": {},
                        "source": "zep_thread"
                    })
                facts_result = {"zep_facts": facts}
            
            # Get Zep users
            users = memory_service.get_zep_users(username, limit)
            
            users_result = {"zep_users": users}
            
            return JsonResponse({
                "success": True,
                "data": {
                    "entities": entities_result.get("zep_entities", []),
                    "facts": facts_result.get("zep_facts", []),
                    "users": users_result.get("zep_users", []),
                    "total_entities": len(entities_result.get("zep_entities", [])),
                    "total_facts": len(facts_result.get("zep_facts", [])),
                    "total_users": len(users_result.get("zep_users", [])),
                    "timestamp": datetime.utcnow().isoformat(),
                    "zep_entities": entities_result.get("zep_entities", []),
                    "zep_facts": facts_result.get("zep_facts", []),
                    "zep_users": users_result.get("zep_users", []),
                    "zep_entities_count": len(entities_result.get("zep_entities", [])),
                    "zep_facts_count": len(facts_result.get("zep_facts", [])),
                    "zep_users_count": len(users_result.get("zep_users", [])),
                    "user_id": username,
                    "session_id": "assistant_ui",
                    "limit": limit,
                    "scope": scope,
                    "query": "",
                    "memory_type": None,
                    "use_zep": True,
                    "reranker": "cross_encoder"
                }
            })
        elif scope == "nodes":
            result = memory_service.search_memories_enhanced(
                username, "", "assistant_ui", limit, None, True, "nodes", "cross_encoder"
            )
            users = memory_service.get_zep_users(username, limit)
            return JsonResponse({
                "success": True,
                "data": {
                    "entities": result.get("zep_entities", []),
                    "users": users,
                    "total_entities": len(result.get("zep_entities", [])),
                    "total_users": len(users),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
        elif scope == "edges":
            result = memory_service.search_memories_enhanced(
                username, "", "assistant_ui", limit, None, True, "edges", "cross_encoder"
            )
            users = memory_service.get_zep_users(username, limit)
            return JsonResponse({
                "success": True,
                "data": {
                    "facts": result.get("zep_facts", []),
                    "users": users,
                    "total_facts": len(result.get("zep_facts", [])),
                    "total_users": len(users),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
        else:
            return JsonResponse({
                "success": False,
                "error": "Invalid scope parameter. Use 'nodes', 'edges', or 'both'"
            }, status=400)
            
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
def search_knowledge_graph(request):
    """
    Search the knowledge graph for specific entities or facts
    
    Query parameters:
    - query: Search query (required)
    - limit: Maximum number of results to return (default: 50)
    - scope: Search scope - 'nodes' for entities, 'edges' for facts, or 'both' (default: 'both')
    """
    try:
        username = request.username_from_token
        
        query = request.GET.get("query")
        if not query:
            return JsonResponse({
                "success": False,
                "error": "Query parameter is required"
            }, status=400)
        
        limit = int(request.GET.get("limit", 50))
        scope = request.GET.get("scope", "both")
        
        if scope == "both":
            # Search both entities and facts from the assistant_ui session (where AI stores memories)
            entities_result = memory_service.search_memories_enhanced(
                username, query, "assistant_ui", limit, None, True, "nodes", "cross_encoder"
            )
            facts_result = memory_service.search_memories_enhanced(
                username, query, "assistant_ui", limit, None, True, "edges", "cross_encoder"
            )
            
            # Handle both Zep and MongoDB results
            entities = entities_result.get("zep_entities", [])
            facts = facts_result.get("zep_facts", [])
            
            # If no Zep results, try to convert MongoDB results
            if not entities and entities_result.get("memories"):
                entities = []
                for memory in entities_result.get("memories", []):
                    entities.append({
                        "id": memory.get("_id", ""),
                        "name": memory.get("content", "")[:50] + "...",
                        "type": memory.get("type", "memory"),
                        "summary": memory.get("content", ""),
                        "attributes": {}
                    })
            
            if not facts and facts_result.get("memories"):
                facts = []
                for memory in facts_result.get("memories", []):
                    facts.append({
                        "fact": memory.get("content", ""),
                        "confidence": 0.8,
                        "source": "mongodb"
                    })
            
            return JsonResponse({
                "success": True,
                "query": query,
                "data": {
                    "entities": entities,
                    "facts": facts,
                    "total_entities": len(entities),
                    "total_facts": len(facts),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
        elif scope == "nodes":
            result = memory_service.search_memories_enhanced(
                username, query, "assistant_ui", limit, None, True, "nodes", "cross_encoder"
            )
            
            entities = result.get("zep_entities", [])
            if not entities and result.get("memories"):
                entities = []
                for memory in result.get("memories", []):
                    entities.append({
                        "id": memory.get("_id", ""),
                        "name": memory.get("content", "")[:50] + "...",
                        "type": memory.get("type", "memory"),
                        "summary": memory.get("content", ""),
                        "attributes": {}
                    })
            
            return JsonResponse({
                "success": True,
                "query": query,
                "data": {
                    "entities": entities,
                    "total_entities": len(entities),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
        elif scope == "edges":
            result = memory_service.search_memories_enhanced(
                username, query, "assistant_ui", limit, None, True, "edges", "cross_encoder"
            )
            
            facts = result.get("zep_facts", [])
            if not facts and result.get("memories"):
                facts = []
                for memory in result.get("memories", []):
                    facts.append({
                        "fact": memory.get("content", ""),
                        "confidence": 0.8,
                        "source": "mongodb"
                    })
            
            return JsonResponse({
                "success": True,
                "query": query,
                "data": {
                    "facts": facts,
                    "total_facts": len(facts),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
        else:
            return JsonResponse({
                "success": False,
                "error": "Invalid scope parameter. Use 'nodes', 'edges', or 'both'"
            }, status=400)
            
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
def add_entity_to_graph(request):
    """
    Add an entity to the knowledge graph
    
    Expected JSON payload:
    {
        "name": "Entity name",
        "labels": ["label1", "label2"],
        "attributes": {...} (optional),
        "summary": "Entity summary" (optional)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        name = data.get("name")
        labels = data.get("labels", [])
        attributes = data.get("attributes", {})
        summary = data.get("summary", "")
        
        if not name:
            return JsonResponse({
                "success": False,
                "error": "Entity name is required"
            }, status=400)
        
        if not labels:
            return JsonResponse({
                "success": False,
                "error": "Entity labels are required"
            }, status=400)
        
        # Create entity data
        entity_data = {
            "name": name,
            "labels": labels if isinstance(labels, list) else [labels],
            "attributes": attributes,
            "summary": summary
        }
        
        # Add to graph using the memory service
        result = memory_service.store_memory_enhanced(
            username, 
            json.dumps(entity_data), 
            "entity", 
            "assistant_ui", 
            {"entity_type": "knowledge_graph_entity"}, 
            True
        )
        
        if result["success"]:
            return JsonResponse({
                "success": True,
                "message": "Entity added successfully",
                "data": entity_data,
                "timestamp": datetime.utcnow().isoformat()
            })
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
def add_fact_to_graph(request):
    """
    Add a fact to the knowledge graph
    
    Expected JSON payload:
    {
        "fact": "Fact content",
        "source": "source_name" (optional)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        fact = data.get("fact")
        source = data.get("source", "user_input")
        
        if not fact:
            return JsonResponse({
                "success": False,
                "error": "Fact content is required"
            }, status=400)
        
        # Create fact data
        fact_data = {
            "fact": fact,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to graph using the memory service
        result = memory_service.store_memory_enhanced(
            username, 
            json.dumps(fact_data), 
            "fact", 
            "assistant_ui", 
            {"fact_type": "knowledge_graph_fact"}, 
            True
        )
        
        if result["success"]:
            return JsonResponse({
                "success": True,
                "message": "Fact added successfully",
                "data": fact_data,
                "timestamp": datetime.utcnow().isoformat()
            })
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
def add_document_to_graph(request):
    """
    Add a document to the knowledge graph
    
    Expected JSON payload:
    {
        "content": "Document content",
        "title": "Document title" (optional),
        "source": "source_name" (optional)
    }
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        
        content = data.get("content")
        title = data.get("title", "Untitled Document")
        source = data.get("source", "user_upload")
        
        if not content:
            return JsonResponse({
                "success": False,
                "error": "Document content is required"
            }, status=400)
        
        # Create document data
        document_data = {
            "content": content,
            "title": title,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to graph using the memory service
        result = memory_service.store_memory_enhanced(
            username, 
            json.dumps(document_data), 
            "document", 
            "assistant_ui", 
            {"document_type": "knowledge_graph_document"}, 
            True
        )
        
        if result["success"]:
            return JsonResponse({
                "success": True,
                "message": "Document added successfully",
                "data": document_data,
                "timestamp": datetime.utcnow().isoformat()
            })
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
