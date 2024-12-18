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
from .forms import UserProfileForm
import pymongo
import json
import re


@api_view(["GET"])
def update_user_profile(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
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
    db = client["myDatabase"]
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
