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


@api_view(["GET"])
def dashboard(request, username):
    # Render the dashboard template with the username
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    user = user_collection.find_one({"username": username})
    first_name = user.get(
        "first_name", "User"
    )  # Default to 'User' if first name is not set
    files = user.get("files", "files")  # Default to 'User' if first name is not set
    devices = user.get(
        "devices", "devices"
    )  # Default to 'User' if first name is not set
    return render(
        request,
        "dashboard.html",
        {
            "username": username,
            "first_name": first_name,
            "files": files,
            "devices": devices,
        },
    )



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_session(request, username):
    # Parse the JSON body
    data = json.loads(request.body)
    task_device = data.get("task_device")

    if not task_device:
        return JsonResponse(
            {"result": "no_device_provided", "message": "No device provided."},
            status=400,
        )
    if not username:
        return JsonResponse(
            {"result": "no_username_provided", "message": "No username provided."},
            status=400,
        )

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    try:
        session_collection = db["sessions"]
    except:
        return JsonResponse({"error": "Can't find session collection"})

    sessions = session_collection.find({
        "username": username,
        "task_device": task_device,
    })

    all_sessions_data = []
    # Convert the cursor to a list of dictionaries and serialize ObjectId to string
    for session in sessions:
        all_sessions_data.append({
            "task_id": session["_id"],
            "task_name": session["task_name"],
            "task_device": session["task_device"],
            "task_status": session["task_status"],
            "task_progress": session["task_progress"],
            "task_date_added": session["task_date_added"],
            "task_date_modified": session["task_date_modified"],
        })

    response_data = {"result": "success", "sessions": all_sessions_data}

    return JsonResponse(response_data, status=200)



@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_view(["GET", "POST"])
def get_recent_session(request, username):
    # Parse the JSON body
    data = json.loads(request.body)
    task_device = data.get("task_device")

    if not task_device:
        return JsonResponse(
            {"result": "no_device_provided", "message": "No device provided."},
            status=400,
        )
    if not username:
        return JsonResponse(
            {"result": "no_username_provided", "message": "No username provided."},
            status=400,
        )

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    try:
        session_collection = db["sessions"]
    except:
        return JsonResponse({"error": "Can't find session collection"})

    sessions = session_collection.find({
        "username": username,
        "task_device": task_device,
    })

    all_sessions_data = []
    for session in sessions:
        # Use .get() with default values for all fields
        all_sessions_data.append({
            "task_id": str(session["_id"]),
            "task_name": session.get("task_name", ""),
            "task_device": session.get("task_device", ""),
            "task_progress": session.get("task_progress", 0),  # Default to 0
            "task_status": session.get("task_status", "unknown"),  # Default to "unknown"
            "task_date_added": session.get("task_date_added", None),
            "task_date_modified": session.get("task_date_modified", None)
        })

    response_data = {"sessions": all_sessions_data}
    return JsonResponse(response_data, status=200)



