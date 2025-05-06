from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import bcrypt
from django.shortcuts import render, redirect
from django.http import JsonResponse
from ..forms import LoginForm
import requests as http_requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import api_view, permission_classes
import pymongo
from datetime import datetime
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv
import os
import base64
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')



@api_view(["GET"])
def login(request):
    """Handles user login via a traditional form (GET displays form, POST processes it)."""
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



# Configure Google OAuth2
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

# Create the flow object
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=SCOPES
)

def google(request):
    """Initiates the Google OAuth2 authentication flow."""
    flow.redirect_uri = REDIRECT_URI
    
    # Generate the authorization URL without state
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return JsonResponse({
        "authUrl": authorization_url
    })

def google_callback(request):
    """Handles the callback from Google after OAuth2 authentication."""
    code = request.GET.get("code")
    
    if not code:
        return JsonResponse({
            "success": False,
            "error": "No authorization code provided"
        }, status=400)
    
    try:
        # Reset the flow with the same scopes
        flow.redirect_uri = REDIRECT_URI
        
        # Exchange the authorization code for credentials
        flow.fetch_token(code=code)
        
        # Get the ID token from credentials
        credentials = flow.credentials
        
        # Verify the ID token
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        user_info = {
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "first_name": id_info.get("given_name"),
            "last_name": id_info.get("family_name"),
            "picture": id_info.get("picture")
        }
        
        return JsonResponse({
            "success": True,
            "user": user_info,
            "id_info": id_info,
            "message": "Successfully authenticated with Google"
        })
        
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def login_api(request):
    """Handles API-based user login with username and password."""
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



@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def register(request):
    """Registers a new user, potentially using Google OAuth profile information."""
    # WE ARE USING THIS ENDPOINT AGAIN IN 3.3


    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        first_name = data.get("first_name") 
        last_name = data.get("last_name")
        phone_number = data.get("phone_number")
        email = data.get("email")
        picture = data.get("picture")  # URL from Google OAuth

        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        user = user_collection.find_one({"username": username})


        # Download and convert the image to base64 if picture_url exists
        profile_picture = None
        if picture:
            try:
                response = http_requests.get(picture, verify=True)
                if response.status_code == 200:
                    # Convert image to base64 for storage
                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    # Print length to verify we have complete data
                    print(f"Base64 string length: {len(image_base64)}")
                    
                    profile_picture = {
                        'data': image_base64,
                        'content_type': response.headers.get('content-type', 'image/jpeg'),
                        'source': 'google_oauth',
                        'size': len(response.content),  # Add original size for verification
                        'base64_length': len(image_base64)  # Add base64 length for verification
                    }
                    
                    # Verify the data can be decoded back
                    try:
                        test_decode = base64.b64decode(image_base64)
                        print(f"Successfully verified base64 data: {len(test_decode)} bytes")
                    except Exception as decode_error:
                        print(f"Base64 verification failed: {decode_error}")
                        
            except Exception as e:
                print(f"Error downloading profile picture: {e}")
                print(f"Response status: {response.status_code if 'response' in locals() else 'No response'}")
                profile_picture = picture  # Store URL as fallback


        password_bytes = password.encode("utf-8")
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        if user:
            user_data = {"result": "user_already_exists", "username": username}
            return JsonResponse(user_data)

        new_user = {
            "username": username,
            "password": hashed_password,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "email": email,
            "picture": profile_picture,  # Store either the base64 image data or URL
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

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@api_view(["GET"])
def new_register(request, username, password, firstName, lastName):
    """Registers a new user with basic information (username, password, names)."""
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
    """Authenticates a user based on username and password (version 4). Duplicate of the one in users/views.py?"""
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



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_site_visitor_info(request):
    """Records information about site visitors, including IP-based geolocation."""
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        # Extract specific data from the JSON (for example: device_id and date_added)
        ip_address = data.get("ip_address")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Fetch location data based on the IP address
    try:
        api_key = "9ab07cc6f5a49eeb6ad0c6f5cc04e34d"
        geo_response = http_requests.get(f"http://api.ipapi.com/api/{ip_address}?access_key={api_key}")
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            city = geo_data.get("city", "Unknown")
            region = geo_data.get("region", "Unknown")
            country = geo_data.get("country_name", "Unknown")
        else:
            city = "Unknown"
            region = "Unknown"
            country = "Unknown"
    except http_requests.RequestException:
        city = "Unknown"
        region = "Unknown"
        country = "Unknown"

    time = datetime.now()

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    site_collection = db["site"]

    # Prepare the document to insert
    new_visitor = {
        "ip_address": ip_address,
        "time": time,
        "city": city,
        "region": region,
        "country": country,
    }

    try:
        site_collection.insert_one(new_visitor)
        result = "success"
    except Exception as e:
        print(f"Error inserting to MongoDB: {e}")
        result = "failed"

    # Return the result
    return JsonResponse({"result": result})


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def token_obtain_pair(request):
    """
    Authenticates a user and returns JWT access and refresh tokens.
    """
    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Find user
        user = user_collection.find_one({"username": username})
        
        if not user:
            return Response(
                {"error": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Verify password
        password_bytes = password.encode("utf-8")
        if not bcrypt.checkpw(password_bytes, user["password"]):
            return Response(
                {"error": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate tokens
        refresh = RefreshToken()
        
        # Add user data to token payload
        refresh["username"] = user["username"]
        refresh["first_name"] = user.get("first_name")
        refresh["last_name"] = user.get("last_name")
        refresh["email"] = user.get("email")
        
        # Get device ID or generate one if not available
        device_id = f"{username}-{os.uname()[1]}"
        
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "username": username,
            "deviceId": device_id,
            "result": "success"
        })
        
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Refreshes a JWT token using a valid refresh token.
    
    Importantly, this preserves all user details from the original token.
    """
    try:
        data = json.loads(request.body)
        refresh_token = data.get("refresh")
        
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract the token first to get the user data
        try:
            # Validate the refresh token
            old_refresh = RefreshToken(refresh_token)
            
            # Print the token payload for debugging
            print(f"Original refresh token payload: {old_refresh.payload}")
            
            # Extract user data from the old token
            payload = old_refresh.payload
            username = payload.get('username')
            
            if not username:
                print("WARNING: No username found in the refresh token")
                # Try to find the user by other means if available
                uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
                client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
                db = client["NeuraNet"]
                user_collection = db["users"]
                
                # If we have user_id, try to get username
                if 'user_id' in payload:
                    user = user_collection.find_one({"_id": payload['user_id']})
                    if user:
                        username = user.get("username")
                
                if not username:
                    return Response(
                        {"error": "Could not identify user from refresh token"}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            # Generate new tokens
            new_refresh = RefreshToken()
            
            # Copy over all the claims from the old token
            for key in payload:
                if key not in ['exp', 'iat', 'jti', 'token_type']:  # Skip standard JWT claims
                    new_refresh[key] = payload[key]
            
            # Ensure username is set
            new_refresh['username'] = username
            
            # Debug the new token payload
            print(f"New refresh token payload: {new_refresh.payload}")
            
            return Response({
                "access": str(new_refresh.access_token),
                "refresh": str(new_refresh),
                "username": username,
                "result": "success"
            })
            
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


