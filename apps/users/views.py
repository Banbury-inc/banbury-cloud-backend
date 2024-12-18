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
def get_small_user_info(request, username):
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
    db = client["myDatabase"]
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