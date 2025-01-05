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
from bson import json_util
import base64
from .forms import UserProfileForm


@api_view(["GET"])
def getuserinfo2(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})
    if not user:
        print("Please login first.")
    else:
        if user["username"] == username:
            first_name = user.get("first_name")
            last_name = user.get("last_name")
            phone_number = user.get("phone_number")
            email = user.get("email")

            devices = user.get("devices", [])
            number_of_files = user.get("number_of_files", [])
            number_of_devices = user.get("number_of_devices", [])
            overall_date_added = user.get("overall_date_added", [])
            total_average_upload_speed = user.get("total_average_upload_speed", [])
            total_average_download_speed = user.get("total_average_download_speed", [])
            total_device_storage = user.get("total_device_storage", [])

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "email": email,
                "devices": devices,
                "number_of_devices": number_of_devices,
                "number_of_files": number_of_files,
                "overall_date_added": overall_date_added,
                "total_average_upload_speed": total_average_upload_speed,
                "total_average_download_speed": total_average_download_speed,
                "total_device_storage": total_device_storage,
            }
            return JsonResponse(user_data)


@api_view(["GET"])
def getuserinfo(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    
    # First check if user exists
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({
            "error": "Please login first.",
            "status": "fail"
        })

    # Get the picture data and handle any ObjectId
    picture_data = user.get("picture", None)
    if picture_data and isinstance(picture_data, dict):
        # Convert any ObjectId in the picture data to string
        picture_data = json.loads(json_util.dumps(picture_data))

    # Safely get all fields with default values
    user_data = {
        "first_name": user.get("first_name", None),
        "last_name": user.get("last_name", None),
        "phone_number": user.get("phone_number", None),
        "email": user.get("email", None),
        "picture": picture_data,
        "devices": json.loads(json_util.dumps(user.get("devices", []))),  # Handle potential ObjectIds in devices
        "status": "success"
    }

    return JsonResponse(user_data, safe=False)



@api_view(["GET"])
def get_small_user_info(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})
    if not user:
        print("Please login first.")
    else:
        if user["username"] == username:
            first_name = user.get("first_name")
            last_name = user.get("last_name")
            phone_number = user.get("phone_number")
            email = user.get("email")

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "email": email,
            }
            return JsonResponse(user_data)



@api_view(["GET"])
def getuserinfo3(request, username, password):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({
            "result": "fail",
            "message": "User not found. Please login first.",
        })

    # Assuming password stored in the database is hashed and saved as bytes.
    # Also assuming 'password' parameter from the function call is the plaintext password to verify.
    stored_hashed_password = user["password"]
    password_bytes = password.encode("utf-8")  # Encode the plaintext password to bytes

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get("username")
    else:
        result = "fail"
        username = None

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@api_view(["GET"])
def getuserinfo4(request, username, password):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({
            "result": "fail",
            "message": "User not found. Please login first.",
        })

    # Assuming password stored in the database is hashed and saved as bytes.
    # Also assuming 'password' parameter from the function call is the plaintext password to verify.
    try:
        stored_hashed_password = user["password"]
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    try:
        password_bytes = password.encode(
            "utf-8"
        )  # Encode the plaintext password to bytes
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get("username")
    else:
        result = "fail"
        username = None

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)



@api_view(["GET"])
def update_user_profile(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["NeuraNet"]
    user_collection = db["users"]

    user = user_collection.find_one({"username": username})

    if request.method == "POST":
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "first_name": form.cleaned_data["first_name"]
                        or user["first_name"],
                        "last_name": form.cleaned_data["last_name"]
                        or user["last_name"],
                        "phone_number": form.cleaned_data["phone_number"]
                        or user["phone_number"],
                        "email": form.cleaned_data["email"] or user["email"],
                    }
                },
            )
            return redirect("dashboard", username=username)
    else:
        form = UserProfileForm(initial=user)

    return render(request, "update_profile.html", {"form": form, "username": username})




@api_view(["GET"])
def change_profile(request, username, password, first_name, last_name, email):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({
            "result": "fail",
            "message": "User not found. Please login first.",
        })

    if password == "undefined":
        user_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "email": email,
                }
            },
        )
    else:
        password_bytes = password.encode("utf-8")  # Encode the string to bytes
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

        user_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "email": email,
                    "password": hashed_password,
                }
            },
        )

    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)

@api_view(["GET"])
def get_profile_picture(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    
    user = user_collection.find_one({"username": username})
    if user and 'picture' in user:
        picture_data = user['picture']
        if isinstance(picture_data, dict) and 'data' in picture_data:
            try:
                # Try to decode the base64 data
                image_bytes = base64.b64decode(picture_data['data'])
                content_type = picture_data.get('content_type', 'image/jpeg')
                return HttpResponse(image_bytes, content_type=content_type)
            except Exception as e:
                print(f"Error decoding image: {e}")
                return HttpResponse(status=400)
    return HttpResponse(status=404)