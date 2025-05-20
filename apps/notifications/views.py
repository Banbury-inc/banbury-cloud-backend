from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .get_notifications import get_notifications as db_get_notifications
from .add_notification import add_notification as db_add_notification
from .delete_notification import delete_notification as db_delete_notification
from .mark_notification_as_read import mark_notification_as_read as db_mark_notification_as_read
import json


@csrf_exempt
@require_http_methods(["GET"])
def get_notifications(request):
    """
    Retrieves all notifications for a specific user.

    Args:
        request: The HTTP request object.
        username: The username of the user whose notifications are to be retrieved.

    Returns:
        JsonResponse: A JSON response containing the list of notifications
                      or an error message.
    """
    try:
        # Since we're not using request parameters, we just pass username directly
        username = request.username_from_token
        notifications = db_get_notifications(username)
        return JsonResponse({
            "result": "success",
            "notifications": notifications,
            "username": request.username_from_token,
        }, safe=False)
    except Exception as e:
        return JsonResponse({
            "result": "fail",
            "error": str(e)
        }, status=500)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_notification(request):
    """
    Adds a new notification for a specific user.

    Expects a JSON body with a "notification" key.

    Args:
        request: The HTTP request object.
        username: The username of the user for whom the notification is added.

    Returns:
        JsonResponse: A JSON response indicating the result of the operation.
    """
    try:
        data = json.loads(request.body)
        notification = data.get("notification")
        username = request.username_from_token
        response = db_add_notification(username, notification)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def delete_notification(request):
    """
    Deletes a specific notification for a user.

    Expects a JSON body with a "notification_id" key.

    Args:
        request: The HTTP request object.
        username: The username of the user whose notification is to be deleted.

    Returns:
        JsonResponse: A JSON response indicating the result of the operation.
    """
    try:
        data = json.loads(request.body)
        notification_id = data.get("notification_id")
        username = request.username_from_token
        response = db_delete_notification(username, notification_id)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def mark_notification_as_read(request):
    """
    Marks a specific notification as read based on its ID.

    Expects a JSON body with a "notification_id" key.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response indicating the result of the operation.
    """
    try:
        data = json.loads(request.body)
        notification_id = data.get("notification_id")
        response = db_mark_notification_as_read(notification_id)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
