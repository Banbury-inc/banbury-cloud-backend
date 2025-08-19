from django.views.decorators.csrf import csrf_exempt
import base64
import os
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
from .utils import generate_api_key, validate_api_key, register_api_key, list_user_api_keys, delete_api_key
from django.views.decorators.csrf import csrf_exempt
import requests
from urllib.parse import urlencode

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



# Configure Google OAuth2 - Minimal initial scopes
MINIMAL_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

# All available scopes for incremental authorization
ALL_SCOPES = {
    "profile": [
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.settings.basic"
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar"
    ]
}

# Legacy scopes for backward compatibility
LEGACY_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/calendar",
    "openid"
]

# Create the flow object with minimal scopes
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
    scopes=MINIMAL_SCOPES
)

def google(request):
    """Initiates the Google OAuth2 authentication flow."""
    # Allow the frontend to specify the redirect URI
    frontend_redirect_uri = request.GET.get('redirect_uri', REDIRECT_URI)
    
    # Validate the redirect URI for security
    allowed_redirect_uris = [
        # Localhost callbacks
        'http://localhost:3000/authentication/auth/callback',
        'http://localhost:3001/authentication/auth/callback',
        'http://localhost:3002/authentication/auth/callback',
        'http://localhost:8080/authentication/auth/callback',
        'http://localhost:3000/files/google_drive/oauth_callback',
        'http://localhost:3001/files/google_drive/oauth_callback',
        'http://localhost:3002/files/google_drive/oauth_callback',
        'http://localhost:8080/files/google_drive/oauth_callback',
        # Production/Dev HTTPS callbacks
        'https://banbury.io/authentication/auth/callback',
        'https://www.banbury.io/authentication/auth/callback',
        'https://dev.banbury.io/authentication/auth/callback',
        'https://www.dev.banbury.io/authentication/auth/callback',
        # Fallback to configured REDIRECT_URI
        REDIRECT_URI
    ]
    
    if frontend_redirect_uri not in allowed_redirect_uris:
        return JsonResponse({
            "error": "Invalid redirect URI"
        }, status=400)
    
    # Create a new flow instance with the correct redirect URI and minimal scopes
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
        scopes=MINIMAL_SCOPES
    )
    flow_instance.redirect_uri = frontend_redirect_uri
    
    # Generate the authorization URL without state
    # Configure optional state and include_granted_scopes via env for flexibility/testing
    use_state = os.environ.get('OAUTH_USE_STATE') == '1'
    include_granted = os.environ.get('OAUTH_INCLUDE_GRANTED_SCOPES', 'true').lower() == 'true'

    kwargs = {
        'access_type': 'offline',
        'include_granted_scopes': 'true' if include_granted else 'false',
        'prompt': 'consent',
    }

    if use_state:
        try:
            state_payload = {"scopes": MINIMAL_SCOPES, "type": "initial"}
            encoded_state = base64.urlsafe_b64encode(json.dumps(state_payload).encode()).decode()
            kwargs['state'] = encoded_state
        except Exception:
            pass

    authorization_url, _ = flow_instance.authorization_url(**kwargs)
    
    return JsonResponse({
        "authUrl": authorization_url
    })

@csrf_exempt
@require_http_methods(["GET"])
def google_callback(request):
    """Handles the callback from Google after OAuth2 authentication."""
    code = request.GET.get("code")
    incoming_redirect_uri = request.GET.get("redirect_uri")
    
    # Add debugging information
    print(f"Google callback received - Code: {code[:10] if code else 'None'}..., Redirect URI: {incoming_redirect_uri}")
    print(f"REDIRECT_URI env var: {REDIRECT_URI}")
    print(f"All query params: {dict(request.GET)}")
    
    if not code:
        return JsonResponse({
            "success": False,
            "error": "No authorization code provided"
        }, status=400)
    
    try:
        # Determine which redirect URI was used based on the request parameter or known list
        # Allowed/known redirect URIs
        allowed_redirect_uris = [
            # Localhost callbacks
            'http://localhost:3000/authentication/auth/callback',
            'http://localhost:3001/authentication/auth/callback',
            'http://localhost:3002/authentication/auth/callback',
            'http://localhost:8080/authentication/auth/callback',
            # Production/Dev HTTPS callbacks
            'https://banbury.io/authentication/auth/callback',
            'https://www.banbury.io/authentication/auth/callback',
            'https://dev.banbury.io/authentication/auth/callback',
            'https://www.dev.banbury.io/authentication/auth/callback',
            # Fallback to configured REDIRECT_URI
            REDIRECT_URI
        ]

        # Build a prioritized list: try the incoming redirect_uri first if valid
        possible_redirect_uris = []
        if incoming_redirect_uri and incoming_redirect_uri in allowed_redirect_uris:
            possible_redirect_uris.append(incoming_redirect_uri)
        # Then extend with the rest, preserving order and avoiding duplicates
        for uri in allowed_redirect_uris:
            if uri and uri not in possible_redirect_uris:
                possible_redirect_uris.append(uri)
        
        # If no redirect URIs were found, use the default
        if not possible_redirect_uris:
            possible_redirect_uris = [REDIRECT_URI]
            print(f"No valid redirect URIs found, using default: {REDIRECT_URI}")
        
        print(f"Will try these redirect URIs: {possible_redirect_uris}")
        
        credentials = None
        used_redirect_uri = None
        attempt_errors = []  # collect debug info for failures
        
        # Reconstruct scopes: prefer scopes encoded in state, then 'scope' param
        granted_scopes_list = None
        state_param = request.GET.get('state')
        if state_param:
            try:
                decoded = base64.urlsafe_b64decode(state_param.encode()).decode()
                state_obj = json.loads(decoded)
                if isinstance(state_obj, dict) and isinstance(state_obj.get('scopes'), list):
                    granted_scopes_list = state_obj['scopes']
                    print(f"Scopes from state: {granted_scopes_list}")
            except Exception as e:
                print(f"Failed parsing state scopes: {e}")
        if not granted_scopes_list:
            granted_scope_param = request.GET.get('scope')
            if granted_scope_param:
                try:
                    granted_scopes_list = granted_scope_param.split(' ')
                    print(f"Granted scopes from callback param: {granted_scopes_list}")
                except Exception as e:
                    print(f"Failed parsing granted scopes: {e}")

        # Only use the incoming redirect URI to avoid consuming the code on multiple attempts
        if incoming_redirect_uri and incoming_redirect_uri in allowed_redirect_uris:
            redirect_uri = incoming_redirect_uri
        else:
            return JsonResponse({
                "success": False,
                "error": "Invalid or missing redirect URI",
                "details": {
                    "incoming_redirect_uri": incoming_redirect_uri,
                    "allowed_redirect_uris": allowed_redirect_uris
                }
            }, status=400)

        # Decide scopes to use for token exchange: prefer granted scopes from callback
        scopes_to_use = granted_scopes_list if granted_scopes_list else MINIMAL_SCOPES

        try:
            print(f"Exchanging code with redirect_uri={redirect_uri} and scopes={scopes_to_use}")
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
                scopes=scopes_to_use
            )
            flow_instance.redirect_uri = redirect_uri
            flow_instance.fetch_token(code=code)
            credentials = flow_instance.credentials
            used_redirect_uri = redirect_uri
            print("Successfully exchanged code for credentials.")
        except Exception as e:
            print(f"Token exchange failed: {e}")
            attempt_errors.append({
                "redirect_uri": redirect_uri,
                "scopes": scopes_to_use,
                "error": str(e)
            })
        
        if not credentials:
            print("Failed to exchange authorization code for credentials after trying all combinations")
            return JsonResponse({
                "success": False,
                "error": "Failed to exchange authorization code for credentials.",
                "details": {
                    "incoming_redirect_uri": incoming_redirect_uri,
                    "tried_redirect_uris": possible_redirect_uris,
                    "attempts": attempt_errors
                }
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
        print(f"Error in google_callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "error": f"Authentication failed: {str(e)}"
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
        password = data.get("password")
        
        if not username or not password:
            return JsonResponse({"error": "Username and password are required"}, status=400)
        
        password = password.encode("utf-8")

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



# ------------------------
# Gmail API proxy endpoints
# ------------------------

def _get_mongo_user_by_username(username: str):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    return user_collection.find_one({"username": username})


def _refresh_google_access_token_if_needed(credentials: dict, user_doc: dict):
    """Ensure we have a valid access token; refresh using refresh_token when required.

    Returns a tuple: (access_token: str, updated_credentials: dict or None)
    If credentials are refreshed, the caller should persist them to Mongo.
    """
    access_token = credentials.get("access_token")
    refresh_token = credentials.get("refresh_token")
    token_uri = credentials.get("token_uri") or "https://oauth2.googleapis.com/token"

    # Attempt a lightweight token introspection by calling a protected endpoint with the token
    # We'll treat 401 responses as an indicator to refresh.
    probe = requests.get(
        "https://www.googleapis.com/oauth2/v1/tokeninfo",
        params={"access_token": access_token},
        timeout=10
    )
    if probe.status_code == 200 and access_token:
        return access_token, None

    # Refresh if we have a refresh token
    if not refresh_token:
        return access_token or "", None

    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post(token_uri, data=data, timeout=15)
    if resp.status_code == 200:
        token_payload = resp.json()
        new_access_token = token_payload.get("access_token")
        if new_access_token:
            updated = dict(credentials)
            updated["access_token"] = new_access_token
            # expiry may be returned as seconds; store best-effort
            if "expires_in" in token_payload:
                try:
                    updated["expiry"] = (datetime.utcnow() + timedelta(seconds=int(token_payload["expires_in"])) ).isoformat()
                except Exception:
                    pass

            # Persist back to Mongo
            try:
                uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
                client = MongoClient(uri)
                db = client["NeuraNet"]
                user_collection = db["users"]
                user_collection.update_one(
                    {"_id": user_doc.get("_id")},
                    {"$set": {"google_drive_credentials": updated}}
                )
            except Exception:
                pass

            return new_access_token, updated

    return access_token or "", None


def _require_auth_username(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or ' ' not in auth_header:
        return None
    try:
        _type, token = auth_header.split(' ', 1)
        validated = AccessToken(token)
        return validated.payload.get('username')
    except Exception:
        return None


@csrf_exempt
@require_http_methods(["GET"])
def gmail_list_messages(request):
    """List Gmail messages for the authenticated user. Optional query params: labelIds, maxResults, pageToken, q."""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    label_ids = request.GET.getlist('labelIds') or request.GET.get('labelIds')
    if isinstance(label_ids, str):
        label_ids = [label_ids]
    max_results = request.GET.get('maxResults', '25')
    page_token = request.GET.get('pageToken')
    query = request.GET.get('q')

    params = {"maxResults": max_results}
    if label_ids:
        # Gmail API supports repeated labelIds or comma-separated; requests will handle repeated if passed as list of tuples
        pass
    if page_token:
        params["pageToken"] = page_token
    if query:
        params["q"] = query

    # Build URL and handle repeated labelIds
    base_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    query_items = list(params.items())
    if label_ids:
        for lid in label_ids:
            query_items.append(("labelIds", lid))
    url = f"{base_url}?{urlencode(query_items)}"

    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if resp.status_code != 200:
        return JsonResponse({"message": "Failed to list messages", "status": resp.status_code, "error": resp.text}, status=resp.status_code)
    return JsonResponse(resp.json())


@csrf_exempt
@require_http_methods(["GET"])
def gmail_get_message(request, message_id):
    """Get a specific Gmail message (full format)."""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if resp.status_code != 200:
        return JsonResponse({"message": "Failed to get message", "status": resp.status_code, "error": resp.text}, status=resp.status_code)
    return JsonResponse(resp.json())


@csrf_exempt
@require_http_methods(["POST"])
def gmail_send_message(request):
    """Send an email via Gmail. Expects JSON: to, subject, body (HTML allowed), cc?, bcc?"""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    to_addr = payload.get("to")
    subject = payload.get("subject", "")
    html_body = payload.get("body", "")
    cc = payload.get("cc")
    bcc = payload.get("bcc")
    is_draft = payload.get("isDraft", False)
    
    # For drafts, we don't require a recipient
    if not is_draft and not to_addr:
        return JsonResponse({"message": "Recipient 'to' is required"}, status=400)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    # Construct RFC 822 email
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart('alternative')
    if to_addr:
        msg['To'] = to_addr
    msg['Subject'] = subject
    # Best-effort from header: use user's email if available
    sender_email = (user_doc.get('email') or username)
    if sender_email:
        msg['From'] = sender_email
    if cc:
        msg['Cc'] = cc
    if bcc:
        msg['Bcc'] = bcc

    # Plain text fallback stripped from HTML
    try:
        import re
        text_body = re.sub('<[^<]+?>', '', html_body)
    except Exception:
        text_body = html_body

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    # Base64url encode
    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode('utf-8')
    
    if is_draft:
        # Create draft
        draft_url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        resp = requests.post(
            draft_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"message": {"raw": raw_b64}},
            timeout=20
        )
        if resp.status_code not in (200, 201):
            return JsonResponse({"message": "Failed to create draft", "status": resp.status_code, "error": resp.text}, status=resp.status_code)
    else:
        # Send message
        send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        resp = requests.post(
            send_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"raw": raw_b64},
            timeout=20
        )
        if resp.status_code not in (200, 202):
            return JsonResponse({"message": "Failed to send message", "status": resp.status_code, "error": resp.text}, status=resp.status_code)
    
    return JsonResponse(resp.json())


@csrf_exempt
@require_http_methods(["POST"])
def gmail_modify_message(request, message_id):
    """Modify a Gmail message. Expects JSON: addLabelIds: [], removeLabelIds: []"""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "addLabelIds": payload.get("addLabelIds", []),
            "removeLabelIds": payload.get("removeLabelIds", []),
        },
        timeout=20
    )
    if resp.status_code != 200:
        return JsonResponse({"message": "Failed to modify message", "status": resp.status_code, "error": resp.text}, status=resp.status_code)
    return JsonResponse(resp.json())


@csrf_exempt
def gmail_get_messages_batch(request):
    """Get multiple Gmail messages in a single batch request"""
    print(f"Batch endpoint called with method: {request.method}")
    
    if request.method != "POST":
        return JsonResponse({"error": f"Method {request.method} not allowed. Use POST."}, status=405)
    
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    message_ids = payload.get("messageIds", [])
    if not message_ids:
        return JsonResponse({"message": "No message IDs provided"}, status=400)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    # Use concurrent requests for better performance
    import concurrent.futures
    
    messages = {}
    
    def fetch_message(message_id):
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20
            )
            if resp.status_code == 200:
                return message_id, resp.json()
            else:
                return message_id, {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return message_id, {"error": str(e)}
    
    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all requests
        future_to_id = {executor.submit(fetch_message, msg_id): msg_id for msg_id in message_ids}
        
        # Collect results
        for future in concurrent.futures.as_completed(future_to_id):
            message_id, result = future.result()
            messages[message_id] = result
    
    return JsonResponse({"messages": messages})


@csrf_exempt
@require_http_methods(["GET"])
def gmail_get_attachment(request, message_id, attachment_id):
    """Get a Gmail message attachment."""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    
    if resp.status_code != 200:
        return JsonResponse({"message": "Failed to get attachment", "status": resp.status_code, "error": resp.text}, status=resp.status_code)
    
    return JsonResponse(resp.json())
@csrf_exempt
@require_http_methods(["POST"])
def gmail_test_batch(request):
    """Test endpoint for batch functionality"""
    print("Test batch endpoint called")
    return JsonResponse({"message": "Test batch endpoint working", "method": request.method})


@csrf_exempt
@require_http_methods(["POST"])
def gmail_send_reply(request):
    """
    Send a reply to an existing email message with proper threading.
    
    Expected JSON payload:
    {
        "original_message_id": "message_id_to_reply_to",
        "to": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "cc": "cc@example.com" (optional),
        "bcc": "bcc@example.com" (optional)
    }
    """
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    try:
        data = json.loads(request.body)
        original_message_id = data.get('original_message_id')
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        if not original_message_id or not to or not subject or not body:
            return JsonResponse({
                "error": "Missing required fields: original_message_id, to, subject, body"
            }, status=400)
        
        # Import the send_reply function from files app
        from apps.files.gmail_service import send_reply
        result = send_reply(username, original_message_id, to, subject, body, cc, bcc)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def gmail_get_thread(request):
    """
    Get a specific thread with all its messages.
    
    Query Parameters:
        thread_id: The ID of the thread to retrieve
    """
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)
    
    thread_id = request.GET.get('thread_id')
    
    if not thread_id:
        return JsonResponse({
            "error": "Missing required parameter: thread_id"
        }, status=400)
    
    # Import the get_thread function from files app
    from apps.files.gmail_service import get_thread
    result = get_thread(username, thread_id)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
def gmail_list_threads(request):
    """
    List threads with optional query filtering.
    
    Query Parameters:
        q: Search query (optional)
        maxResults: Maximum number of threads to return (default: 10)
    """
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)
    
    query = request.GET.get('q')
    max_results = int(request.GET.get('maxResults', 10))
    
    # Import the list_threads function from files app
    from apps.files.gmail_service import list_threads
    result = list_threads(username, query, max_results)
    return JsonResponse(result)


# =============================================================================
# Scope Management Endpoints
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def get_user_scopes(request):
    """Get the current scopes for the authenticated user."""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)
    
    try:
        # Import the get_user_drive_credentials function from files app
        from apps.files.google_drive_service import get_user_drive_credentials
        
        credentials = get_user_drive_credentials(username)
        if not credentials:
            return JsonResponse({
                "scopes": [],
                "message": "No Google credentials found"
            })
        
        # Determine which features are available based on scopes
        available_features = {
            "profile": any(scope in credentials.scopes for scope in ALL_SCOPES["profile"]),
            "drive": any(scope in credentials.scopes for scope in ALL_SCOPES["drive"]),
            "gmail": any(scope in credentials.scopes for scope in ALL_SCOPES["gmail"]),
            "calendar": any(scope in credentials.scopes for scope in ALL_SCOPES["calendar"])
        }
        
        return JsonResponse({
            "scopes": credentials.scopes,
            "available_features": available_features,
            "message": "Scopes retrieved successfully"
        })
        
    except Exception as e:
        return JsonResponse({
            "error": f"Failed to get user scopes: {str(e)}"
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def request_additional_scopes(request):
    """Request additional scopes for the authenticated user."""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)
    
    try:
        data = json.loads(request.body)
        requested_features = data.get('features', [])
        
        if not requested_features:
            return JsonResponse({
                "error": "No features specified"
            }, status=400)
        
        # Validate requested features
        valid_features = list(ALL_SCOPES.keys())
        invalid_features = [f for f in requested_features if f not in valid_features]
        if invalid_features:
            return JsonResponse({
                "error": f"Invalid features: {invalid_features}. Valid features: {valid_features}"
            }, status=400)
        
        # Get current scopes
        from apps.files.google_drive_service import get_user_drive_credentials
        credentials = get_user_drive_credentials(username)
        
        if not credentials:
            return JsonResponse({
                "error": "No Google credentials found. Please authenticate with Google first."
            }, status=400)
        
        # Determine which scopes to request
        current_scopes = set(credentials.scopes)
        requested_scopes = set()
        
        for feature in requested_features:
            requested_scopes.update(ALL_SCOPES[feature])
        
        # Only request scopes that aren't already granted
        new_scopes = requested_scopes - current_scopes
        
        if not new_scopes:
            return JsonResponse({
                "message": "All requested scopes are already granted",
                "scopes": list(current_scopes)
            })
        
        # Get the redirect URI from the request
        frontend_redirect_uri = request.GET.get('redirect_uri', REDIRECT_URI)
        
        # Validate the redirect URI for security
        allowed_redirect_uris = [
            'http://localhost:3000/authentication/auth/callback',
            'http://localhost:3001/authentication/auth/callback',
            'http://localhost:3002/authentication/auth/callback',
            'http://localhost:8080/authentication/auth/callback',
            'https://banbury.io/authentication/auth/callback',
            'https://www.banbury.io/authentication/auth/callback',
            'https://dev.banbury.io/authentication/auth/callback',
            'https://www.dev.banbury.io/authentication/auth/callback',
            REDIRECT_URI
        ]
        
        if frontend_redirect_uri not in allowed_redirect_uris:
            return JsonResponse({
                "error": "Invalid redirect URI"
            }, status=400)
        
        # Create OAuth flow with additional scopes
        all_scopes = list(current_scopes) + list(new_scopes)
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
            scopes=all_scopes
        )
        flow_instance.redirect_uri = frontend_redirect_uri
        
        # Generate the authorization URL
        authorization_url, _ = flow_instance.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return JsonResponse({
            "authUrl": authorization_url,
            "requested_features": requested_features,
            "new_scopes": list(new_scopes),
            "message": "Additional scopes authorization URL generated"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({
            "error": f"Failed to request additional scopes: {str(e)}"
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_available_features(request):
    """Get information about available Google features and their required scopes."""
    return JsonResponse({
        "features": {
            "profile": {
                "name": "Profile Information",
                "description": "Access to your Google profile information (name, email, picture)",
                "scopes": ALL_SCOPES["profile"],
                "required": True
            },
            "drive": {
                "name": "Google Drive",
                "description": "Access to read, write, and manage files in your Google Drive",
                "scopes": ALL_SCOPES["drive"],
                "required": False
            },
            "gmail": {
                "name": "Gmail",
                "description": "Access to read, send, and manage your Gmail messages",
                "scopes": ALL_SCOPES["gmail"],
                "required": False
            },
            "calendar": {
                "name": "Google Calendar",
                "description": "Access to read and manage your Google Calendar events",
                "scopes": ALL_SCOPES["calendar"],
                "required": False
            }
        },
        "message": "Available features retrieved successfully"
    })