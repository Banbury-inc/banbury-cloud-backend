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


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
analytics_collection = db["ai"]


@csrf_exempt
@require_http_methods(["POST", "GET"])
@api_view(["POST", "GET"])
def get_models(request):
    # Find the analytics document for this user, or create if it doesn't exist
    analytics = analytics_collection.find_one_and_update(
        {"_id": "analytics"},  # Filter to find the document
        {"$inc": {"file_requests": 1}},  # Update operation to increment file_requests
        upsert=True,  # Create document if it doesn't exist
        return_document=pymongo.ReturnDocument.AFTER  # Return updated document
    )

    return JsonResponse({
        "result": "success", 
        "message": "File request added successfully",
        "file_requests": analytics["file_requests"]
    }, status=200)


@csrf_exempt
@require_http_methods(["POST", "GET"])
@api_view(["POST", "GET"])
def post_models(request):
    # Find the analytics document for this user, or create if it doesn't exist
    analytics = analytics_collection.find_one_and_update(
        {"_id": "analytics"},  # Filter to find the document
        {"$inc": {"file_requests": 1}},  # Update operation to increment file_requests
        upsert=True,  # Create document if it doesn't exist
        return_document=pymongo.ReturnDocument.AFTER  # Return updated document
    )

    return JsonResponse({
        "result": "success", 
        "message": "File request added successfully",
        "file_requests": analytics["file_requests"]
    }, status=200)

