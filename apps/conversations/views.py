from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from .models import Conversation

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
        
        new_title = data.get("title")
        
        if not new_title:
            return JsonResponse({
                "success": False,
                "error": "Title is required"
            }, status=400)
        
        result = Conversation.update_conversation_title(conversation_id, username, new_title)
        
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
