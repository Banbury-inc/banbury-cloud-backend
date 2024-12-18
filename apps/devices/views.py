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
from .remove_device import remove_device
from .get_online_devices import get_online_devices
from .update_device_configuration_preferences import update_device_configuration_preferences as db_update_device_configuration_preferences

import pymongo
import json
import re


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_device(request, username, device_name):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        device_type = data.get("device_type")
        storage_capacity_gb = data.get("storage_capacity_gb")
        sync_storage_capacity_gb = data.get("sync_storage_capacity_gb")
        date_added = data.get("date_added")
        upload_network_speed = data.get("upload_network_speed")
        download_network_speed = data.get("download_network_speed")
        gpu_usage = data.get("gpu_usage")
        cpu_usage = data.get("cpu_usage")
        ram_usage = data.get("ram_usage")
        ram_total = data.get("ram_total")
        ram_free = data.get("ram_free")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    device_collection = db["devices"]
    user_collection = db["users"]

    # Find the user_id based on username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"result": "error", "message": "Device not found."})

    user_id = user["_id"]  # Get the ObjectId for the device

    new_device = {
        "user_id": user_id,
        "device_name": device_name,
        "device_type": device_type,
        "storage_capacity_gb": storage_capacity_gb,
        "sync_storage_capacity_gb": sync_storage_capacity_gb,
        "date_added": [],
        "upload_network_speed": [],
        "download_network_speed": [],
        "gpu_usage": [],
        "cpu_usage": [],
        "ram_usage": [],
        "ram_total": [],
        "ram_free": [],
        "sync_status": False,
        "online": True,
    }

    try:
        # Insert the new device and get the inserted_id
        result = device_collection.insert_one(new_device)
        device_id = result.inserted_id

        # Update the user collection to add the device_id to the user's list of devices
        user_collection.update_one({"_id": user_id}, {"$push": {"devices": device_id}})

        # Append all usage data and other arrays in the device document
        device_collection.update_one(
            {"_id": device_id},
            {
                "$push": {
                    "gpu_usage": gpu_usage,
                    "cpu_usage": cpu_usage,
                    "ram_usage": ram_usage,
                    "ram_total": ram_total,
                    "ram_free": ram_free,
                    "download_network_speed": download_network_speed,
                    "upload_network_speed": upload_network_speed,
                    "date_added": date_added,
                }
            },
        )

    except Exception as e:
        print(f"Error sending to device: {e}")

    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def delete_device(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        response = remove_device(username, device_name)
        if response == "success":
            return JsonResponse({
                "result": "success",
                "message": "Device deleted successfully.",
            })
        else:
            return JsonResponse({
                "result": "fail",
                "message": "Device not deleted.",
            })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)





@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_view(["GET", "POST"])
def update_device_configuration_preferences(request, username):
    data = json.loads(request.body)
    device_name = data.get("device_name")
    device_configurations = {
        "use_predicted_cpu_usage": data.get("use_predicted_cpu_usage"),
        "use_predicted_gpu_usage": data.get("use_predicted_gpu_usage"),
        "use_predicted_ram_usage": data.get("use_predicted_ram_usage"),
        "use_predicted_download_speed": data.get("use_predicted_download_speed"),
        "use_predicted_upload_speed": data.get("use_predicted_upload_speed"),
        "use_files_needed": data.get("use_files_needed"),
        "use_files_available_for_download": data.get("use_files_available_for_download"),
    }
    result = db_update_device_configuration_preferences(username, device_name, device_configurations)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)



@api_view(["GET"])
def getdeviceinfo(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({"error": "Please login first."}, status=401)

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))

    # Prepare devices data for response
    device_data = []
    for device in devices:
        device_data.append({
            "device_name": device.get("device_name"),
            "device_type": device.get("device_type"),
            "storage_capacity_gb": device.get("storage_capacity_gb"),
            "device_manufacturer": device.get("device_manufacturer"),
            "device_model": device.get("device_model"),
            "device_version": device.get("device_version"),
            "cpu_info_manufacturer": device.get("cpu_info_manufacturer"),
            "cpu_info_brand": device.get("cpu_info_brand"),
            "cpu_info_speed": device.get("cpu_info_speed"),
            "cpu_info_cores": device.get("cpu_info_cores"),
            "cpu_info_physical_cores": device.get("cpu_info_physical_cores"),
            "cpu_info_processors": device.get("cpu_info_processors"),
            "date_added": device.get("date_added"),
            "upload_speed": device.get("upload_speed"),
            "download_speed": device.get("download_speed"),
            "battery_status": device.get("battery_status"),
            "gpu_usage": device.get("gpu_usage"),
            "cpu_usage": device.get("cpu_usage"),
            "ram_usage": device.get("ram_usage"),
            "ram_total": device.get("ram_total"),
            "ram_free": device.get("ram_free"),
            "sync_status": device.get("sync_status"),
            "online": device.get("online"),
            "scanned_folders": device.get("scanned_folders"),
        })

    device_data = {
        "devices": device_data,
    }

    return JsonResponse(device_data)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def handle_get_online_devices(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    response = get_online_devices(username)

    if response == "fail":
        return JsonResponse({"result": "fail", "message": "fail"})
    if response == "success":
        return JsonResponse({
            "result": "success",
            "message": "Files deleted successfully.",
        })



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def declare_device_online(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        user_data = {"result": "fail cant find user", "username": username}
        return JsonResponse(user_data)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        # Return success response
        user_data = {"result": "fail cant find device", "username": username}
        return JsonResponse(user_data)

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"online": True}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def declare_device_offline(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"online": False}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)
