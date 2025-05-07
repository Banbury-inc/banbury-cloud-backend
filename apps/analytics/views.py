from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
from rest_framework.decorators import api_view
import pymongo


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
analytics_collection = db["analytics"]


@csrf_exempt
@require_http_methods(["POST", "GET"])
@api_view(["POST", "GET"])
def add_file_request(request):
    """Increments the file_requests count in the analytics collection."""
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
def add_file_request_success(request):
    """Increments the file_requests_success count in the analytics collection."""
    # Find the analytics document for this user, or create if it doesn't exist
    analytics = analytics_collection.find_one_and_update(
        {"_id": "analytics"},  # Filter to find the document
        {"$inc": {"file_requests_success": 1}},  # Update operation to increment file_requests_success
        upsert=True,  # Create document if it doesn't exist
        return_document=pymongo.ReturnDocument.AFTER  # Return updated document
    )

    return JsonResponse({
        "result": "success", 
        "message": "File request added successfully",
        "file_requests_success": analytics["file_requests_success"]
    }, status=200)



@csrf_exempt
@require_http_methods(["GET"])
@api_view(["GET"])
def get_analytics(request):
    """Retrieves analytics data for a specific user."""

    response_data = {"result": "success", "analytics": "analytics"}

    return JsonResponse(response_data, status=200)



