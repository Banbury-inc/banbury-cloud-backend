from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import os
from bson import ObjectId
import pymongo
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .forms import UserForm
import bcrypt
from .forms import LoginForm
from .forms import UserProfileForm
import json
import re




@api_view(["GET"])
def homepage(request):
    service = os.environ.get("K_SERVICE", "Unknown service")
    revision = os.environ.get("K_REVISION", "Unknown revision")

    return render(
        request,
        "homepage.html",
        context={
            "message": "It's running!",
            "Service": service,
            "Revision": revision,
        },
    )

