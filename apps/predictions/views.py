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
from .get_device_predictions import get_device_predictions as db_get_device_predictions
from .update_sync_storage_capacity import update_sync_storage_capacity as db_update_sync_storage_capacity
from .get_download_queue import get_download_queue as db_get_download_queue
from .db_add_file_to_sync import db_add_file_to_sync as db_add_file_to_sync
from .pipeline import pipeline
from .get_file_sync import get_file_sync as db_get_file_sync
from .update_file_priority import update_file_priority as db_update_file_priority
import pymongo
import json
import re


@csrf_exempt
@require_http_methods(["GET"])
@api_view(["GET"])
def run_pipeline(request, username):
    result = pipeline(username)
    response_data = {
        "result": "success",
        "data": result,
    }   
    return JsonResponse(response_data)



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def add_file_to_sync(request, username):
    data = json.loads(request.body)
    device_name = data.get("device_name")
    file_path = data.get("file_path")
    response = db_add_file_to_sync(username, device_name, file_path)

    user_data = {
        "result": response,
        "username": username,  # Return username if success, None if fail
    }

    return JsonResponse(user_data)



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_files_to_sync(request, username):
    try:
        # Parse request body
        data = json.loads(request.body)
        global_file_path = data.get('global_file_path')
        
        # Call database function with optional global_file_path
        response, status_code = db_get_file_sync(username, global_file_path)
        
        if status_code != 200:
            return JsonResponse({
                "result": "error",
                "message": response.get("error", "Unknown error occurred"),
                "files": []
            }, status=status_code)
            
        return JsonResponse({
            "result": "success",
            "files": response.get("files", [])
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "result": "error",
            "message": "Invalid JSON",
            "files": []
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "error",
            "message": str(e),
            "files": []
        }, status=500)



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def update_file_priority(request, username):
    try:
        data = json.loads(request.body)
        file_id = data.get("file_id")
        priority = data.get("priority")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    response = db_update_file_priority(username, file_id, priority)


    files_data = {
        "result": response.get("result"),
        "message": response.get("message"),
    }



    return JsonResponse(files_data)



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def update_sync_storage_capacity(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        storage_capacity = data.get("storage_capacity")
        response = db_update_sync_storage_capacity(username, device_name, storage_capacity)

        print(response)

        files_data = {
            "result": response.get("result"),
            "message": response.get("message"),
        }

        return JsonResponse(files_data)



    except json.JSONDecodeError:

        return JsonResponse({"error": "Invalid JSON"}, status=400)



@csrf_exempt
@require_http_methods(["POST"])
def get_download_queue(request, username):
    try:
        data = json.loads(request.body)
        device_id = data.get("device_id")
        response = db_get_download_queue(username, device_id)
        print("response: ", response)
        return JsonResponse({
            "result": "success",
            "download_queue": response,
            "message": "Download queue retrieved successfully",
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
@require_http_methods(["GET"])
@api_view(["GET"])
def get_device_prediction_data(request, username):
    result = db_get_device_predictions(username)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)