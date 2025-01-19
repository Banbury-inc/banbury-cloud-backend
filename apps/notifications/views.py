from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import bcrypt
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from ..forms import LoginForm
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .get_notifications import get_notifications as db_get_notifications
from .add_notification import add_notification as db_add_notification
from .delete_notification import delete_notification as db_delete_notification
from .mark_notification_as_read import mark_notification_as_read as db_mark_notification_as_read
import pymongo
import json
import re



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["GET"])
@api_view(["GET"])
def get_notifications(request, username):
    try:
        # Since we're not using request parameters, we just pass username directly
        notifications = db_get_notifications(username)
        return JsonResponse({
            "result": "success",
            "notifications": notifications,
            "username": username
        }, safe=False)
    except Exception as e:
        return JsonResponse({
            "result": "fail",
            "error": str(e)
        }, status=500)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_notification(request, username):
    try:
        data = json.loads(request.body)
        notification = data.get("notification")
        response = db_add_notification(username, notification)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def delete_notification(request, username):
    try:
        data = json.loads(request.body)
        notification_id = data.get("notification_id")
        response = db_delete_notification(username, notification_id)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def mark_notification_as_read(request):
    try:
        data = json.loads(request.body)
        notification_id = data.get("notification_id")
        response = db_mark_notification_as_read(notification_id)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
