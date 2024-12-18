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
from datetime import datetime
from bson.objectid import ObjectId


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_task(request, username):
    try:
        data = json.loads(request.body)
        task_name = data.get("task_name")
        task_device = data.get("task_device")
        task_progress = data.get("task_progress")
        task_status = data.get("task_status")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    session_collection = db["sessions"]
    device_collection = db["devices"]

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": task_device})
    if not device:
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        })

    try:
        device_id = device["_id"]  # Get the ObjectId for the device
    except:
        return JsonResponse({
            "result": "object_id_not_found",
            "message": "Device id not found.",
        })

    new_task = {
        "device_id": device_id,
        "username": username,
        "task_name": task_name,
        "task_device": task_device,
        "task_status": task_status,
        "task_progress": task_progress,
        "task_date_added": datetime.now(),
        "task_date_modified": datetime.now(),
    }

    try:
        result = session_collection.insert_one(new_task)
        return JsonResponse({
            "result": "success",
            "username": username,
            "task_id": str(result.inserted_id)  # Return the task ID
        })
    except Exception as e:
        return JsonResponse({"result": "error", "message": str(e)})



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def update_task(request, username):
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")  # Get task_id instead of task_name
        task_progress = data.get("task_progress")
        task_status = data.get("task_status")
        task_name = data.get("task_name")  # Optional for updating name
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    session_collection = db["sessions"]

    update_fields = {
        "task_status": task_status,
        "task_progress": task_progress,
        "task_date_modified": datetime.now(),
    }
    if task_name:
        update_fields["task_name"] = task_name

    update_result = session_collection.update_one(
        {"_id": ObjectId(task_id)},  # Use task_id to find the task
        {"$set": update_fields}
    )

    if update_result.matched_count == 0:
        return JsonResponse({"result": "task_not_found", "message": "Task not found."})

    return JsonResponse({
        "result": "success",
        "task_id": str(task_id),
        "message": "Task status updated successfully.",
    })


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def fail_task(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

        task_name = data.get("task_name")
        task_progress = data.get("task_progress")
        result = data.get("result")
        task_device = data.get(
            "task_device"
        )  # You may also want to use the device name for better specificity
        task_status = data.get("task_status")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    session_collection = db["sessions"]

    # Use both task_name and task_device to find the specific task
    query = {"task_name": task_name}
    if task_device:
        query["task_device"] = task_device

    # Update the task with the new status and update the task_date_modified field
    update_result = session_collection.update_one(
        query,
        {
            "$set": {
                "task_status": task_status,
                "task_name": result,
                "task_progress": task_progress,
                "task_date_modified": datetime.now(),  # Update the modification date
            }
        },
    )

    if update_result.matched_count == 0:
        return JsonResponse({"result": "task_not_found", "message": "Task not found."})

    return JsonResponse({
        "result": "success",
        "message": "Task status updated successfully.",
    })
