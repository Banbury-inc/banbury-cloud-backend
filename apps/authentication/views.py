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
def login(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    user_collection = db["users"]

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"].encode("utf-8")

            user = user_collection.find_one({"username": username})

            if user and bcrypt.checkpw(password, user["password"]):
                return redirect(
                    "dashboard", username=username
                )  # Redirect to a home page or dashboard
            else:
                return render(
                    request,
                    "login.html",
                    {"form": form, "error": "Invalid username or password"},
                )
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["GET"])
def login_api(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    # Ensure the request body is JSON
    try:
        data = json.loads(request.body)

        # extract username and password from the JSON data
        username = data.get("username")
        password = data.get("password").encode("utf-8")

        user = user_collection.find_one({"username": username})

        if user and bcrypt.checkpw(password, user["password"]):
            return JsonResponse({"response": "success"})
        else:
            return JsonResponse({"response": "fail"})

    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)



@api_view(["GET"])
def register(request, username, password, firstName, lastName):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    password_bytes = password.encode("utf-8")  # Encode the string to bytes
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    if user:
        user_data = {"result": "user_already_exists", "username": username}
        return JsonResponse(user_data)

    new_user = {
        "username": username,
        "password": hashed_password,
        "first_name": firstName,
        "last_name": lastName,
        "phone_number": None,
        "email": None,
        "devices": [],
        "number_of_devices": [],
        "number_of_files": [],
        "overall_date_added": [],
        "total_average_download_speed": [],
        "total_average_upload_speed": [],
        "total_device_storage": [],
        "total_average_cpu_usage": [],
        "total_average_gpu_usage": [],
        "total_average_ram_usage": [],
    }

    try:
        user_collection.insert_one(new_user)
    except Exception as e:
        print(f"Error sending to device: {e}")
    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@api_view(["GET"])
def new_register(request, username, password, firstName, lastName):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    password_bytes = password.encode("utf-8")  # Encode the string to bytes
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    if user:
        user_data = {"result": "user_already_exists", "username": username}
        return JsonResponse(user_data)

    new_user = {
        "username": username,
        "password": hashed_password,
        "first_name": firstName,
        "last_name": lastName,
        "phone_number": None,
        "email": None,
        "devices": [],
    }

    try:
        user_collection.insert_one(new_user)
    except Exception as e:
        print(f"Error sending to device: {e}")
    result = "success"

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


