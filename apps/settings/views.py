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
import pymongo
import json
import re


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def update_settings(request, username):
    try:
        data = json.loads(request.body)
        sync_entire_device_checked = data.get("sync_entire_device_checked")
        predicted_upload_speed_weighting = data.get("predicted_upload_speed_weighting")
        predicted_download_speed_weighting = data.get("predicted_download_speed_weighting")
        predicted_cpu_usage_weighting = data.get("predicted_cpu_usage_weighting")
        predicted_ram_usage_weighting = data.get("predicted_ram_usage_weighting")
        predicted_gpu_usage_weighting = data.get("predicted_gpu_usage_weighting")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    settings_collection = db["settings"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    user_id = user["_id"]

    # Check if settings already exist for this user
    existing_settings = settings_collection.find_one({
        "user_id": user_id
    })

    settings_data = {
        "sync_entire_device_checked": sync_entire_device_checked,
        "predicted_upload_speed_weighting": predicted_upload_speed_weighting,
        "predicted_download_speed_weighting": predicted_download_speed_weighting,
        "predicted_cpu_usage_weighting": predicted_cpu_usage_weighting,
        "predicted_ram_usage_weighting": predicted_ram_usage_weighting,
        "predicted_gpu_usage_weighting": predicted_gpu_usage_weighting,
    }

    try:
        if existing_settings:
            # Update existing settings
            settings_collection.update_one(
                {"_id": existing_settings["_id"]},
                {"$set": settings_data}
            )
            message = "Settings updated successfully"
        else:
            # Create new settings
            settings_data.update({
                "user_id": user_id
            })
            settings_collection.insert_one(settings_data)
            message = "Settings created successfully"

        return JsonResponse({
            "result": "success",
            "message": message,
            "username": username
        })

    except Exception as e:
        print(f"Error updating settings: {e}")
        return JsonResponse({
            "result": "error",
            "message": str(e)
        }, status=500)