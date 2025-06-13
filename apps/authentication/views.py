from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.permissions import AllowAny
import bcrypt
from django.shortcuts import render, redirect
from django.http import JsonResponse
from ..forms import LoginForm
import requests as http_requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import permission_classes, authentication_classes, api_view
import pymongo
from datetime import datetime, timedelta
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv
import os
import base64
import jwt
from rest_framework_simplejwt.tokens import AccessToken
from django.conf import settings
from rest_framework.response import Response
from .utils import generate_api_key, validate_api_key, register_api_key
from django.views.decorators.csrf import csrf_exempt

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')



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
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
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
    # Allow the frontend to specify the redirect URI
    frontend_redirect_uri = request.GET.get('redirect_uri', REDIRECT_URI)
    
    # Validate the redirect URI for security
    allowed_redirect_uris = [
        'http://localhost:3000/authentication/auth/callback',
        'http://localhost:3001/authentication/auth/callback',
        'http://localhost:3002/authentication/auth/callback',
        'http://localhost:3000/files/google_drive/oauth_callback',
        'http://localhost:3001/files/google_drive/oauth_callback',
        'http://localhost:3002/files/google_drive/oauth_callback',
        REDIRECT_URI  # Keep the original environment variable as fallback
    ]
    
    if frontend_redirect_uri not in allowed_redirect_uris:
        return JsonResponse({
            "error": "Invalid redirect URI"
        }, status=400)
    
    # Create a new flow instance with the correct redirect URI
    flow_instance = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [frontend_redirect_uri],
            }
        },
        scopes=SCOPES
    )
    flow_instance.redirect_uri = frontend_redirect_uri
    
    # Generate the authorization URL without state
    authorization_url, _ = flow_instance.authorization_url(
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
        # Determine which redirect URI was used based on the referrer or a parameter
        # For now, we'll try the most common ones
        possible_redirect_uris = [
            'http://localhost:3000/authentication/auth/callback',
            'http://localhost:3001/authentication/auth/callback',
            'http://localhost:3002/authentication/auth/callback',
            REDIRECT_URI
        ]
        
        credentials = None
        used_redirect_uri = None
        
        # Try each possible redirect URI until one works
        for redirect_uri in possible_redirect_uris:
            try:
                # Create a new flow instance for this redirect URI
                flow_instance = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": GOOGLE_CLIENT_ID,
                            "client_secret": GOOGLE_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [redirect_uri],
                        }
                    },
                    scopes=SCOPES
                )
                flow_instance.redirect_uri = redirect_uri
                
                # Try to exchange the code for credentials
                flow_instance.fetch_token(code=code)
                credentials = flow_instance.credentials
                used_redirect_uri = redirect_uri
                break
            except Exception as e:
                # This redirect URI didn't work, try the next one
                continue
        
        if not credentials:
            return JsonResponse({
                "success": False,
                "error": "Failed to exchange authorization code for credentials"
            }, status=400)
        
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
        
        # Now handle user authentication/creation and token generation
        email = user_info.get("email")
        if not email:
            return JsonResponse({
                "success": False,
                "error": "No email provided by Google"
            }, status=400)
        
        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Check if user exists by email
        user = user_collection.find_one({"email": email})
        
        # Store Google Drive credentials
        drive_credentials = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        if not user:
            # Create new user for Google OAuth
            # Download and convert the profile picture if available
            profile_picture = None
            if user_info.get("picture"):
                try:
                    response = http_requests.get(user_info["picture"], verify=True)
                    if response.status_code == 200:
                        image_base64 = base64.b64encode(response.content).decode('utf-8')
                        profile_picture = {
                            'data': image_base64,
                            'content_type': response.headers.get('content-type', 'image/jpeg'),
                            'source': 'google_oauth',
                            'size': len(response.content)
                        }
                except Exception as e:
                    print(f"Error downloading profile picture: {e}")
                    profile_picture = user_info.get("picture")  # Store URL as fallback
            
            new_user = {
                "username": email,  # Use email as username for Google OAuth users
                "email": email,
                "first_name": user_info.get("first_name"),
                "last_name": user_info.get("last_name"),
                "picture": profile_picture,
                "phone_number": None,
                "password": None,  # No password for OAuth users
                "auth_method": "google_oauth",
                "devices": [],
                "google_drive_credentials": drive_credentials,
            }
            
            try:
                user_collection.insert_one(new_user)
                user = new_user
            except Exception as e:
                print(f"Error creating user: {e}")
                return JsonResponse({
                    "success": False,
                    "error": "Failed to create user"
                }, status=500)
        else:
            # Update existing user with new Google Drive credentials
            try:
                # For existing users, update by both email and username (in case they differ)
                # First try to update by email
                result = user_collection.update_one(
                    {"email": email},
                    {"$set": {"google_drive_credentials": drive_credentials}}
                )
                
                # Also update by username if the user has username set to email (common for Google OAuth users)
                if email:
                    user_collection.update_one(
                        {"username": email},
                        {"$set": {"google_drive_credentials": drive_credentials}}
                    )
                
                user["google_drive_credentials"] = drive_credentials
                print(f"Successfully updated Google Drive credentials for user: {email}")
                
            except Exception as e:
                print(f"Error updating user with Drive credentials: {e}")
                # Continue without failing the login
        
        # Generate a JWT token for the user
        access = AccessToken()
        access["username"] = user.get("username") or email
        # Set token expiry to 7 days
        access.set_exp(lifetime=timedelta(days=7))
        token = str(access)
        
        return JsonResponse({
            "success": True,
            "user": {
                "email": email,
                "username": user.get("username") or email,
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "picture": user.get("picture")
            },
            "token": token,
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


@authentication_classes([])
@permission_classes([AllowAny])
def getuserinfo4(request, username, password):
    """Authenticates a user based on username and password (version 4)."""
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

    try:
        stored_hashed_password = user["password"]
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    try:
        password_bytes = password.encode("utf-8")
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get("username")
        
        # Generate a valid Simple JWT access token without hitting the DB
        access = AccessToken()
        access["username"] = username
        # Set token expiry to 7 days
        access.set_exp(lifetime=timedelta(days=7))
        token = str(access)
    else:
        result = "fail"
        username = None
        token = None

    user_data = {
        "result": result,
        "username": username,
        "token": token if result == "success" else None,
    }
    return JsonResponse(user_data)


def validate_token(request):
    """
    Validates the current token by simply returning a success response.
    The authentication middleware will already validate the token.
    """
    username = request.username_from_token
    return JsonResponse({
        "valid": True,
        "username": username
    })

def refresh_token(request):
    """
    Generates a new access token based on the username in the current token.
    """
    try:
        # Get username from the existing token
        username = request.username_from_token
        
        if not username:
            return JsonResponse({
                "success": False,
                "message": "Invalid token"
            }, status=401)
        
        # Generate a new token
        access = AccessToken()
        access["username"] = username
        
        # Set token expiry to 7 days
        access.set_exp(lifetime=timedelta(days=7))
        
        return JsonResponse({
            "success": True,
            "token": str(access),
            "username": username
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=401)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
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
@require_http_methods(["POST"])
def generate_user_api_key(request):
    """
    Generate a new API key for the authenticated user
    Only authenticated users can generate API keys
    """
    try:
        # Get authenticated user information
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)
            
        # Validate token and get username
        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
                
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)
        
        # Get the user document from MongoDB to get the _id
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)
        
        # Extract the MongoDB _id
        user_id = str(user.get('_id'))
        
        # Parse request body
        data = json.loads(request.body) if request.body else {}
        role = data.get('role', 'user')  # Default role is 'user'
        
        # Generate and register the API key
        new_api_key = generate_api_key()
        register_api_key(new_api_key, user_id=user_id, role=role)
        
        return JsonResponse({
            'api_key': new_api_key,
            'username': username,
            'user_id': user_id,
            'role': role,
            'message': 'Your new API key has been generated. Keep it secure - it will not be shown again.'
        })
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def validate_user_api_key(request):
    """
    Validate an API key
    """
    try:
        data = json.loads(request.body)
        api_key = data.get('api_key')
        if not api_key:
            return JsonResponse({'valid': False, 'message': 'No API key provided'}, status=400)
        
        is_valid = validate_api_key(api_key)
        
        # Get additional details if valid
        details = None
        if is_valid:
            details = get_api_key_details(api_key)
        
        return JsonResponse({
            'valid': is_valid,
            'message': 'API key is valid' if is_valid else 'Invalid API key',
            'details': details
        })
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'valid': False, 'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def list_api_keys(request):
    """
    List all API keys for the authenticated user
    """
    try:
        # Get authenticated user information
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)
            
        # Validate token and get username
        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
                
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)
        
        # Get the user document from MongoDB to get the _id
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)
        
        # Extract the MongoDB _id
        user_id = str(user.get('_id'))
        
        # Get all keys for the user
        keys = list_user_api_keys(user_id)
        
        return JsonResponse({
            'username': username,
            'user_id': user_id,
            'api_keys': keys
        })
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_user_api_key(request):
    """
    Delete an API key
    """
    try:
        # Get authenticated user information
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)
            
        # Validate token and get username
        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
                
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)
        
        # Get the user document from MongoDB to get the _id
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)
        
        # Extract the MongoDB _id
        user_id = str(user.get('_id'))
        
        # Parse request body
        data = json.loads(request.body)
        api_key = data.get('api_key')
        
        if not api_key:
            return JsonResponse({'message': 'No API key provided'}, status=400)
        
        # Check that the API key belongs to the user
        details = get_api_key_details(api_key)
        if not details or details.get('user_id') != user_id:
            return JsonResponse({'message': 'API key not found or not authorized'}, status=403)
        
        # Delete the API key
        deleted = delete_api_key(api_key)
        
        return JsonResponse({
            'success': deleted,
            'message': 'API key deleted successfully' if deleted else 'Failed to delete API key'
        })
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)


