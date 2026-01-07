from django.views.decorators.csrf import csrf_exempt
import base64
import os
import hashlib
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
from .email_service import email_service
from django.views.decorators.csrf import csrf_exempt
import requests
from urllib.parse import urlencode
import urllib.parse

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
        "https://www.googleapis.com/auth/gmail.labels",
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
    "https://www.googleapis.com/auth/gmail.labels",
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
@authentication_classes([])
@permission_classes([AllowAny])
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
        
        # Reconstruct scopes: prefer 'scope' param from Google callback; normalize short names
        def normalize_scopes(scopes: list) -> list:
            mapping = {
                'email': 'https://www.googleapis.com/auth/userinfo.email',
                'profile': 'https://www.googleapis.com/auth/userinfo.profile',
            }
            result = []
            for s in scopes:
                s2 = mapping.get(s, s)
                if s2 not in result:
                    result.append(s2)
            return result

        granted_scopes_list = None
        granted_scope_param = request.GET.get('scope')
        if granted_scope_param:
            try:
                granted_scopes_list = normalize_scopes(granted_scope_param.split(' '))
                print(f"Granted scopes from callback param (normalized): {granted_scopes_list}")
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
            # Avoid oauthlib scope mismatch parsing by unsetting client scope before parsing response
            try:
                flow_instance.client.scope = None
            except Exception:
                pass
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
            # If the error tells us scopes have changed, extract them and retry once
            try:
                msg = str(e)
                marker = ' to "'
                if 'Scope has changed' in msg and marker in msg:
                    new_scopes_str = msg.split(marker, 1)[1].rstrip('".')
                    derived_scopes = new_scopes_str.split(' ')
                    print(f"Retrying with scopes derived from error: {derived_scopes}")
                    flow_instance2 = Flow.from_client_config(
                        {
                            "web": {
                                "client_id": GOOGLE_CLIENT_ID,
                                "client_secret": GOOGLE_CLIENT_SECRET,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "redirect_uris": [redirect_uri],
                            }
                        },
                        scopes=derived_scopes
                    )
                    flow_instance2.redirect_uri = redirect_uri
                    try:
                        flow_instance2.client.scope = None
                    except Exception:
                        pass
                    flow_instance2.fetch_token(code=code)
                    credentials = flow_instance2.credentials
                    used_redirect_uri = redirect_uri
                    print("Successfully exchanged code after deriving scopes from error.")
                else:
                    print("No derivable scopes from error message.")
            except Exception as e2:
                print(f"Retry with derived scopes failed: {e2}")
        
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
        
        # Track successful login
        try:
            login_collection = db["user_logins"]
            login_event = {
                "username": user.get("username") or email,
                "user_id": str(user.get("_id")),
                "timestamp": datetime.utcnow(),
                "ip_address": request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')),
                "user_agent": request.META.get('HTTP_USER_AGENT', 'unknown'),
                "auth_method": "google_oauth"
            }
            login_collection.insert_one(login_event)
        except Exception as e:
            print(f"Error tracking Google OAuth login: {e}")
        
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
            
            # Send welcome email after successful user creation
            if email and first_name:
                try:
                    email_sent = email_service.send_welcome_email(
                        user_email=email,
                        user_first_name=first_name,
                        user_last_name=last_name or "",
                        username=username
                    )
                    if email_sent:
                        print(f"Welcome email sent successfully to {email}")
                    else:
                        print(f"Failed to send welcome email to {email}")
                except Exception as email_error:
                    print(f"Error sending welcome email to {email}: {email_error}")
                    # Don't fail registration if email fails
                    
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
        
        # Track successful login
        try:
            login_collection = db["user_logins"]
            login_event = {
                "username": username,
                "user_id": str(user["_id"]),
                "timestamp": datetime.utcnow(),
                "ip_address": request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')),
                "user_agent": request.META.get('HTTP_USER_AGENT', 'unknown'),
                "auth_method": "password"
            }
            login_collection.insert_one(login_event)
        except Exception as e:
            print(f"Error tracking login: {e}")
        
        # Generate a valid Simple JWT access token without hitting the DB
        access = AccessToken()
        access["username"] = username
        # Set token expiry to 7 days
        access.set_exp(lifetime=timedelta(days=7))
        token = str(access)
        
        # Store the bearer token in the user document for daemon access
        try:
            import os
            mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority')
            mongo_client = MongoClient(mongo_uri)
            mongo_db = mongo_client['NeuraNet']
            users_collection = mongo_db['users']
            
            users_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "bearer_token": token,
                        "token_updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            print(f"Warning: Failed to store bearer token for user {username}: {e}")
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



@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_client_ip(request):
    """Get the client's public IP address by fetching it from an external service."""
    try:
        # Get the client's IP address from the request first
        # Check for various headers in order of preference
        
        # 1. Check for CloudFlare headers
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_connecting_ip:
            client_ip = cf_connecting_ip
        # 2. Check for forwarded headers (for proxy/load balancer scenarios)
        elif request.META.get('HTTP_X_FORWARDED_FOR'):
            # Take the first IP in the list (the original client IP)
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0].strip()
        # 3. Check for real IP header
        elif request.META.get('HTTP_X_REAL_IP'):
            client_ip = request.META.get('HTTP_X_REAL_IP')
        # 4. Fall back to REMOTE_ADDR
        else:
            client_ip = request.META.get('REMOTE_ADDR', 'Unknown')
        
        # If we have a valid client IP, use it; otherwise fetch from external service
        if client_ip and client_ip != 'Unknown' and client_ip != '127.0.0.1':
            # Validate IP address format (basic check)
            import re
            ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            if re.match(ip_pattern, client_ip):
                ip_address = client_ip
            else:
                ip_address = 'Unknown'
        else:
            # Fetch public IP from external service (server-side, no CORS issues)
            try:
                import requests
                response = requests.get('https://api.ipify.org?format=json', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    ip_address = data.get('ip', 'Unknown')
                else:
                    ip_address = 'Unknown'
            except Exception:
                # If external service fails, try alternative
                try:
                    response = requests.get('https://api64.ipify.org?format=json', timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        ip_address = data.get('ip', 'Unknown')
                    else:
                        ip_address = 'Unknown'
                except Exception:
                    ip_address = 'Unknown'
        
        # For debugging (only in development)
        if settings.DEBUG:
            print(f"IP Detection Debug - Client IP: {client_ip}, Public IP: {ip_address}")
        
        return Response({"ip": ip_address})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def add_site_visitor_info(request):
    """Records information about site visitors, including IP-based geolocation."""
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        # Extract specific data from the JSON (for example: device_id and date_added)
        ip_address = data.get("ip_address")
        path = data.get("path", "Unknown")
        client_timestamp = data.get("timestamp")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Fetch location data based on the IP address
    city = "Unknown"
    region = "Unknown"
    country = "Unknown"
    
    try:
        # Try primary service: ipapi.com
        api_key = "9ab07cc6f5a49eeb6ad0c6f5cc04e34d"
        geo_response = http_requests.get(f"http://api.ipapi.com/api/{ip_address}?access_key={api_key}")
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            city = geo_data.get("city", "Unknown")
            region = geo_data.get("region", "Unknown")
            country = geo_data.get("country_name", "Unknown")
        else:
            # Try fallback service: ip-api.com (free, no API key required)
            try:
                fallback_response = http_requests.get(f"http://ip-api.com/json/{ip_address}")
                if fallback_response.status_code == 200:
                    fallback_data = fallback_response.json()
                    if fallback_data.get("status") == "success":
                        city = fallback_data.get("city", "Unknown")
                        region = fallback_data.get("regionName", "Unknown")
                        country = fallback_data.get("country", "Unknown")
            except http_requests.RequestException:
                # If fallback also fails, keep default "Unknown" values
                pass
    except http_requests.RequestException:
        # If primary service fails completely, try fallback service
        try:
            fallback_response = http_requests.get(f"http://ip-api.com/json/{ip_address}")
            if fallback_response.status_code == 200:
                fallback_data = fallback_response.json()
                if fallback_data.get("status") == "success":
                    city = fallback_data.get("city", "Unknown")
                    region = fallback_data.get("regionName", "Unknown")
                    country = fallback_data.get("country", "Unknown")
        except http_requests.RequestException:
            # If both services fail, keep default "Unknown" values
            pass

    time = datetime.utcnow()

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    site_collection = db["site"]

    # Prepare the document to insert
    new_visitor = {
        "ip_address": ip_address,
        "path": path,
        "client_timestamp": client_timestamp,
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
def add_site_visitor_info_enhanced(request):
    """Records enhanced information about site visitors, including referrer source and campaign data."""
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        
        # Extract enhanced data from the JSON
        ip_address = data.get("ip_address")
        path = data.get("path", "Unknown")
        client_timestamp = data.get("timestamp")
        page_title = data.get("page_title", "Unknown")
        referrer_source = data.get("referrer_source")
        campaign_id = data.get("campaign_id")
        content_type = data.get("content_type", "web_page")
        user_agent = data.get("user_agent", "Unknown")
        device_type = data.get("device_type", "Unknown")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Fetch location data based on the IP address
    city = "Unknown"
    region = "Unknown"
    country = "Unknown"
    
    try:
        # Try primary service: ipapi.com
        api_key = "9ab07cc6f5a49eeb6ad0c6f5cc04e34d"
        geo_response = http_requests.get(f"http://api.ipapi.com/api/{ip_address}?access_key={api_key}")
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            city = geo_data.get("city", "Unknown")
            region = geo_data.get("region", "Unknown")
            country = geo_data.get("country_name", "Unknown")
        else:
            # Try fallback service: ip-api.com (free, no API key required)
            try:
                fallback_response = http_requests.get(f"http://ip-api.com/json/{ip_address}")
                if fallback_response.status_code == 200:
                    fallback_data = fallback_response.json()
                    if fallback_data.get("status") == "success":
                        city = fallback_data.get("city", "Unknown")
                        region = fallback_data.get("regionName", "Unknown")
                        country = fallback_data.get("country", "Unknown")
            except http_requests.RequestException:
                # If fallback also fails, keep default "Unknown" values
                pass
    except http_requests.RequestException:
        # If primary service fails completely, try fallback service
        try:
            fallback_response = http_requests.get(f"http://ip-api.com/json/{ip_address}")
            if fallback_response.status_code == 200:
                fallback_data = fallback_response.json()
                if fallback_data.get("status") == "success":
                    city = fallback_data.get("city", "Unknown")
                    region = fallback_data.get("regionName", "Unknown")
                    country = fallback_data.get("country", "Unknown")
        except http_requests.RequestException:
            # If both services fail, keep default "Unknown" values
            pass

    time = datetime.utcnow()

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    site_collection = db["site_enhanced"]

    # Prepare the enhanced document to insert
    new_visitor = {
        "ip_address": ip_address,
        "path": path,
        "client_timestamp": client_timestamp,
        "time": time,
        "city": city,
        "region": region,
        "country": country,
        "page_title": page_title,
        "referrer_source": referrer_source,
        "campaign_id": campaign_id,
        "content_type": content_type,
        "user_agent": user_agent,
        "device_type": device_type,
        "tracking_version": "2.0"
    }

    try:
        site_collection.insert_one(new_visitor)
        result = "success"
    except Exception as e:
        print(f"Error inserting enhanced tracking to MongoDB: {e}")
        result = "failed"

    # Return the result
    return JsonResponse({"result": result})

@csrf_exempt
@require_http_methods(["GET"])
def get_site_visitor_info_enhanced(request):
    """Retrieves enhanced site visitor analytics with referrer and campaign data."""
    try:
        # Get query parameters
        limit = int(request.GET.get('limit', 100))
        days = int(request.GET.get('days', 30))
        
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        site_collection = db["site_enhanced"]
        
        # Calculate date filter
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query with date filter and limit
        cursor = site_collection.find({
            "time": {"$gte": start_date}
        }).sort("time", -1).limit(limit)
        
        # Helper functions to parse user agent
        def parse_browser(user_agent):
            """Extract browser name from user agent."""
            if not user_agent or user_agent == "Unknown":
                return "Unknown"
            ua = user_agent.lower()
            if "chrome" in ua and "edg" not in ua:
                return "Chrome"
            elif "firefox" in ua:
                return "Firefox"
            elif "safari" in ua and "chrome" not in ua:
                return "Safari"
            elif "edg" in ua or "edge" in ua:
                return "Edge"
            elif "opera" in ua or "opr" in ua:
                return "Opera"
            elif "msie" in ua or "trident" in ua:
                return "Internet Explorer"
            elif "samsung" in ua:
                return "Samsung Internet"
            return "Other"
        
        def parse_os(user_agent):
            """Extract operating system from user agent."""
            if not user_agent or user_agent == "Unknown":
                return "Unknown"
            ua = user_agent.lower()
            if "windows" in ua:
                if "windows nt 10" in ua:
                    return "Windows 10/11"
                elif "windows nt 6.3" in ua:
                    return "Windows 8.1"
                elif "windows nt 6.2" in ua:
                    return "Windows 8"
                elif "windows nt 6.1" in ua:
                    return "Windows 7"
                return "Windows"
            elif "mac os x" in ua or "macintosh" in ua:
                return "macOS"
            elif "iphone" in ua or "ipad" in ua or "ipod" in ua:
                return "iOS"
            elif "android" in ua:
                return "Android"
            elif "linux" in ua:
                return "Linux"
            elif "ubuntu" in ua:
                return "Ubuntu"
            return "Other"
        
        # Convert to list and prepare response data
        visitors = []
        referrer_stats = {}
        content_stats = {}
        campaign_stats = {}
        device_type_stats = {}
        browser_stats = {}
        os_stats = {}
        page_stats = {}
        ip_visit_counts = {}
        
        for visitor in cursor:
            # Convert ObjectId to string and datetime to ISO string
            visitor_data = {
                "_id": str(visitor["_id"]),
                "ip_address": visitor.get("ip_address", "Unknown"),
                "path": visitor.get("path", "Unknown"),
                "page_title": visitor.get("page_title", "Unknown"),
                "referrer_source": visitor.get("referrer_source"),
                "campaign_id": visitor.get("campaign_id"),
                "content_type": visitor.get("content_type", "web_page"),
                "user_agent": visitor.get("user_agent", "Unknown"),
                "device_type": visitor.get("device_type", "Unknown"),
                "city": visitor.get("city", "Unknown"),
                "region": visitor.get("region", "Unknown"),
                "country": visitor.get("country", "Unknown"),
                "time": visitor["time"].isoformat() if isinstance(visitor["time"], datetime) else str(visitor["time"]),
                "client_timestamp": visitor.get("client_timestamp"),
                "tracking_version": visitor.get("tracking_version", "2.0")
            }
            visitors.append(visitor_data)
            
            # Track IP visit counts for return visitor analysis
            ip = visitor.get("ip_address", "Unknown")
            if ip != "Unknown":
                ip_visit_counts[ip] = ip_visit_counts.get(ip, 0) + 1
            
            # Aggregate statistics
            referrer = visitor.get("referrer_source")
            if referrer:
                referrer_stats[referrer] = referrer_stats.get(referrer, 0) + 1
            
            content_type = visitor.get("content_type", "web_page")
            content_stats[content_type] = content_stats.get(content_type, 0) + 1
            
            campaign = visitor.get("campaign_id")
            if campaign:
                # Truncate long campaign IDs for readability
                campaign_key = campaign[:50] + "..." if len(campaign) > 50 else campaign
                campaign_stats[campaign_key] = campaign_stats.get(campaign_key, 0) + 1
            
            # Device type statistics
            device_type = visitor.get("device_type", "Unknown")
            device_type_stats[device_type] = device_type_stats.get(device_type, 0) + 1
            
            # Browser statistics
            user_agent = visitor.get("user_agent", "Unknown")
            browser = parse_browser(user_agent)
            browser_stats[browser] = browser_stats.get(browser, 0) + 1
            
            # OS statistics
            os = parse_os(user_agent)
            os_stats[os] = os_stats.get(os, 0) + 1
            
            # Top pages/paths statistics
            path = visitor.get("path", "Unknown")
            if path != "Unknown":
                # Clean path (remove query parameters)
                clean_path = path.split('?')[0] if '?' in path else path
                page_stats[clean_path] = page_stats.get(clean_path, 0) + 1
        
        # Calculate return visitors
        unique_visitors = len([ip for ip, count in ip_visit_counts.items() if count == 1])
        return_visitors = len([ip for ip, count in ip_visit_counts.items() if count > 1])
        total_return_visits = sum(count - 1 for count in ip_visit_counts.values() if count > 1)
        
        # Prepare summary statistics
        total_visitors = len(visitors)
        unique_ips = len(set(v["ip_address"] for v in visitors if v["ip_address"] != "Unknown"))
        unique_countries = len(set(v["country"] for v in visitors if v["country"] != "Unknown"))
        
        response_data = {
            "visitors": visitors,
            "summary": {
                "total_visitors": total_visitors,
                "unique_ips": unique_ips,
                "unique_countries": unique_countries,
                "unique_visitors": unique_visitors,
                "return_visitors": return_visitors,
                "total_return_visits": total_return_visits,
                "date_range_days": days,
                "referrer_breakdown": referrer_stats,
                "content_type_breakdown": content_stats,
                "device_type_breakdown": device_type_stats,
                "browser_breakdown": browser_stats,
                "os_breakdown": os_stats,
                "top_pages": dict(sorted(page_stats.items(), key=lambda x: x[1], reverse=True)[:20]),
                "top_campaigns": dict(sorted(campaign_stats.items(), key=lambda x: x[1], reverse=True)[:10])
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error retrieving enhanced visitor info: {e}")
        return JsonResponse({"error": "Failed to retrieve visitor information"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_site_visitor_info_paginated(request):
    """Retrieves paginated site visitor analytics with filtering support."""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 100))
        days = int(request.GET.get('days', 30))
        
        # Filter parameters
        location_filter = request.GET.get('location', '').strip()
        source_filter = request.GET.get('source', '').strip()
        campaign_filter = request.GET.get('campaign', '').strip()
        content_type_filter = request.GET.get('content_type', '').strip()
        ip_exclusions = request.GET.get('ip_exclusions', '').strip()
        
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        site_collection = db["site_enhanced"]
        
        # Calculate date filter
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query filter
        query_filter = {"time": {"$gte": start_date}}
        
        # Add location filter (city, region, or country)
        if location_filter:
            query_filter["$or"] = [
                {"city": {"$regex": location_filter, "$options": "i"}},
                {"region": {"$regex": location_filter, "$options": "i"}},
                {"country": {"$regex": location_filter, "$options": "i"}}
            ]
        
        # Add source filter
        if source_filter:
            query_filter["referrer_source"] = {"$regex": source_filter, "$options": "i"}
        
        # Add campaign filter
        if campaign_filter:
            query_filter["campaign_id"] = {"$regex": campaign_filter, "$options": "i"}
        
        # Add content type filter
        if content_type_filter:
            query_filter["$or"] = [
                {"page_title": {"$regex": content_type_filter, "$options": "i"}},
                {"path": {"$regex": content_type_filter, "$options": "i"}}
            ]
        
        # Add IP exclusions
        if ip_exclusions:
            excluded_ips = [ip.strip() for ip in ip_exclusions.split(',') if ip.strip()]
            if excluded_ips:
                query_filter["ip_address"] = {"$nin": excluded_ips}
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Get total count for pagination info
        total_count = site_collection.count_documents(query_filter)
        total_pages = (total_count + page_size - 1) // page_size
        
        # Query with pagination
        cursor = site_collection.find(query_filter).sort("time", -1).skip(skip).limit(page_size)
        
        # Convert to list and prepare response data
        visitors = []
        for visitor in cursor:
            # Convert ObjectId to string and datetime to ISO string
            visitor_data = {
                "_id": str(visitor["_id"]),
                "ip_address": visitor.get("ip_address", "Unknown"),
                "path": visitor.get("path", "Unknown"),
                "page_title": visitor.get("page_title", "Unknown"),
                "referrer_source": visitor.get("referrer_source"),
                "campaign_id": visitor.get("campaign_id"),
                "content_type": visitor.get("content_type", "web_page"),
                "user_agent": visitor.get("user_agent", "Unknown"),
                "city": visitor.get("city", "Unknown"),
                "region": visitor.get("region", "Unknown"),
                "country": visitor.get("country", "Unknown"),
                "time": visitor["time"].isoformat() if isinstance(visitor["time"], datetime) else str(visitor["time"]),
                "client_timestamp": visitor.get("client_timestamp"),
                "tracking_version": visitor.get("tracking_version", "2.0")
            }
            visitors.append(visitor_data)
        
        # Prepare pagination info
        pagination_info = {
            "current_page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
        response_data = {
            "visitors": visitors,
            "pagination": pagination_info,
            "filters": {
                "location": location_filter,
                "source": source_filter,
                "campaign": campaign_filter,
                "content_type": content_type_filter,
                "ip_exclusions": ip_exclusions,
                "days": days
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error retrieving paginated visitor info: {e}")
        return JsonResponse({"error": "Failed to retrieve visitor information"}, status=500)

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
def calendar_calendars(request):
    """List Google Calendar calendars for the authenticated user.
    GET: list calendars from calendarList.list API
    Returns: { items: CalendarListEntry[], nextPageToken?: string }
    """
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

    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    params = {}
    for key in ["maxResults", "pageToken", "minAccessRole", "showDeleted", "showHidden"]:
        val = request.GET.get(key)
        if val is not None:
            params[key] = val
    if params:
        url += f"?{urlencode(params)}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    return JsonResponse(resp.json(), status=resp.status_code)


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def calendar_events(request, event_id: str = None):
    """Proxy Google Calendar events for the authenticated user.
    GET: list events (query: timeMin, timeMax, maxResults, pageToken, q, singleEvents, orderBy, calendarId)
    POST: create event (json: calendarId?, event)
    PUT: update event (requires eventId path -> use calendar_event_detail)
    DELETE: not supported here.
    """
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

    base = "https://www.googleapis.com/calendar/v3/calendars"
    if request.method == "GET":
        calendar_id = request.GET.get('calendarId', 'primary')
        params = {}
        for key in ["timeMin", "timeMax", "maxResults", "pageToken", "q", "singleEvents", "orderBy"]:
            val = request.GET.get(key)
            if val is not None:
                params[key] = val
        url = f"{base}/{urllib.parse.quote(calendar_id, safe='')}/events"
        if params:
            url += f"?{urlencode(params)}"
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        return JsonResponse(resp.json(), status=resp.status_code)

    if request.method == "POST":
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON"}, status=400)
        calendar_id = payload.get('calendarId', 'primary')
        event = payload.get('event') or {}
        url = f"{base}/{urllib.parse.quote(calendar_id, safe='')}/events"
        resp = requests.post(url, headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}, json=event, timeout=20)
        return JsonResponse(resp.json(), status=resp.status_code)

    return JsonResponse({"message": "Method not allowed"}, status=405)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def calendar_event_detail(request, event_id: str):
    """Get/Update/Delete a single Google Calendar event by ID."""
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

    calendar_id = request.GET.get('calendarId', 'primary')
    base = "https://www.googleapis.com/calendar/v3/calendars"
    url = f"{base}/{urllib.parse.quote(calendar_id, safe='')}/events/{event_id}"

    if request.method == "GET":
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        return JsonResponse(resp.json(), status=resp.status_code)
    if request.method == "PUT":
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON"}, status=400)
        event = payload.get('event') or {}
        resp = requests.put(url, headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}, json=event, timeout=20)
        return JsonResponse(resp.json(), status=resp.status_code)
    if request.method == "DELETE":
        resp = requests.delete(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        if resp.status_code in (200, 204):
            return JsonResponse({"success": True})
        return JsonResponse(resp.json(), status=resp.status_code)

    return JsonResponse({"message": "Method not allowed"}, status=405)


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
@require_http_methods(["GET", "POST"])
def gmail_labels(request):
    """List or create Gmail labels for the authenticated user.

    GET: returns Gmail API labels list (system + user).
    POST: create a new user label. Expects JSON: { name, labelListVisibility?, messageListVisibility? }
    """
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

    base_url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"

    if request.method == "GET":
        # Explicitly request both SYSTEM and USER label types to avoid accidental filtering.
        resp = requests.get(
            base_url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=[("labelTypes", "system"), ("labelTypes", "user")],
            timeout=20
        )
        if resp.status_code != 200:
            return JsonResponse(
                {"message": "Failed to list labels", "status": resp.status_code, "error": resp.text},
                status=resp.status_code
            )

        payload = resp.json() if resp.text else {}
        labels = payload.get("labels", [])
        # Normalize label type casing just in case.
        for label in labels:
            label_type = label.get("type")
            if isinstance(label_type, str):
                label["type"] = label_type.lower()

        return JsonResponse({"labels": labels})

    # POST
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    name = payload.get("name")
    if not name:
        return JsonResponse({"message": "Label 'name' is required"}, status=400)

    create_body = {"name": name}
    if payload.get("labelListVisibility") is not None:
        create_body["labelListVisibility"] = payload.get("labelListVisibility")
    if payload.get("messageListVisibility") is not None:
        create_body["messageListVisibility"] = payload.get("messageListVisibility")

    resp = requests.post(
        base_url,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=create_body,
        timeout=20
    )
    if resp.status_code not in (200, 201):
        return JsonResponse(
            {"message": "Failed to create label", "status": resp.status_code, "error": resp.text},
            status=resp.status_code
        )

    created = resp.json() if resp.text else {}
    created_type = created.get("type")
    if isinstance(created_type, str):
        created["type"] = created_type.lower()

    return JsonResponse(created, status=201)


@csrf_exempt
@require_http_methods(["DELETE"])
def gmail_label_detail(request, label_id: str):
    """Delete a Gmail label by ID for the authenticated user."""
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)

    if not label_id:
        return JsonResponse({"message": "Label ID is required"}, status=400)

    user_doc = _get_mongo_user_by_username(username)
    if not user_doc:
        return JsonResponse({"message": "User not found"}, status=404)

    credentials = user_doc.get("google_drive_credentials") or {}
    access_token, _ = _refresh_google_access_token_if_needed(credentials, user_doc)
    if not access_token:
        return JsonResponse({"message": "No Google credentials on file"}, status=400)

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/labels/{label_id}"
    resp = requests.delete(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if resp.status_code not in (200, 204):
        return JsonResponse(
            {"message": "Failed to delete label", "status": resp.status_code, "error": resp.text},
            status=resp.status_code
        )

    return JsonResponse({"success": True})


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
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
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
def gmail_get_thread(request, thread_id: str):
    """
    Get a specific thread with all its messages.
    
    URL Parameters:
        thread_id: The ID of the thread to retrieve
    """
    username = _require_auth_username(request)
    if not username:
        return JsonResponse({"message": "Authentication required"}, status=401)
    
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
# Google Drive API Proxy Endpoints
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def drive_list_files(request):
    """
    List files from Google Drive for the authenticated user.
    Query Parameters:
        pageSize: Number of files to return (default: 100)
        pageToken: Token for pagination
        q: Query string for filtering files (e.g., 'trashed = false')
        orderBy: Sort order (e.g., 'modifiedTime desc')
        fields: Fields to include in response
    """
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

    # Extract query parameters
    page_size = request.GET.get('pageSize', '100')
    page_token = request.GET.get('pageToken')
    query = request.GET.get('q', 'trashed = false')
    order_by = request.GET.get('orderBy', 'modifiedTime desc')
    fields = request.GET.get('fields', 'files(id,name,mimeType,modifiedTime,createdTime,size,webViewLink,iconLink,thumbnailLink,parents,trashed,starred),nextPageToken')

    # Build URL with query parameters
    params = {
        "pageSize": page_size,
        "q": query,
        "orderBy": order_by,
        "fields": fields
    }
    if page_token:
        params["pageToken"] = page_token

    url = f"https://www.googleapis.com/drive/v3/files?{urlencode(params)}"
    
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to list files",
            "status": resp.status_code,
            "error": resp.text
        }, status=resp.status_code)
    
    return JsonResponse(resp.json())


@csrf_exempt
@require_http_methods(["GET"])
def drive_get_file(request, file_id):
    """
    Get metadata for a specific Google Drive file.
    Query Parameters:
        fields: Fields to include in response
    """
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

    fields = request.GET.get('fields', 'id,name,mimeType,modifiedTime,createdTime,size,webViewLink,iconLink,thumbnailLink,parents,trashed,starred')
    
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields={urllib.parse.quote(fields)}"
    
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to get file",
            "status": resp.status_code,
            "error": resp.text
        }, status=resp.status_code)
    
    return JsonResponse(resp.json())


@csrf_exempt
@require_http_methods(["GET"])
def drive_download_file(request, file_id):
    """
    Download a file from Google Drive.
    Returns the file content as a binary response.
    """
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

    # First get file metadata to get the name and MIME type
    metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType"
    metadata_resp = requests.get(metadata_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    
    if metadata_resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to get file metadata",
            "status": metadata_resp.status_code,
            "error": metadata_resp.text
        }, status=metadata_resp.status_code)
    
    metadata = metadata_resp.json()
    file_name = metadata.get('name', 'download')
    mime_type = metadata.get('mimeType', 'application/octet-stream')

    # Download the file content
    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    download_resp = requests.get(download_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=60, stream=True)
    
    if download_resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to download file",
            "status": download_resp.status_code,
            "error": download_resp.text
        }, status=download_resp.status_code)
    
    # Return the file as a streaming response
    from django.http import HttpResponse
    response = HttpResponse(download_resp.content, content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response


@csrf_exempt
@require_http_methods(["GET"])
def drive_export_file(request, file_id):
    """
    Export a Google Workspace file (Docs, Sheets, Slides) to a specified format.
    Query Parameters:
        mimeType: The MIME type to export to (e.g., application/vnd.openxmlformats-officedocument.wordprocessingml.document for DOCX)
    """
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

    # Get the export MIME type from query parameters
    export_mime_type = request.GET.get('mimeType')
    if not export_mime_type:
        return JsonResponse({"message": "mimeType parameter is required"}, status=400)

    # First get file metadata to get the name
    metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType"
    metadata_resp = requests.get(metadata_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    
    if metadata_resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to get file metadata",
            "status": metadata_resp.status_code,
            "error": metadata_resp.text
        }, status=metadata_resp.status_code)
    
    metadata = metadata_resp.json()
    file_name = metadata.get('name', 'export')
    
    # Determine file extension based on export MIME type
    extension_map = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/pdf': '.pdf',
        'text/plain': '.txt',
        'text/html': '.html',
    }
    extension = extension_map.get(export_mime_type, '')
    if extension and not file_name.lower().endswith(extension):
        file_name += extension

    # Export the file
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType={urllib.parse.quote(export_mime_type)}"
    export_resp = requests.get(export_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=60, stream=True)
    
    if export_resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to export file",
            "status": export_resp.status_code,
            "error": export_resp.text
        }, status=export_resp.status_code)
    
    # Return the exported file as a streaming response
    from django.http import HttpResponse
    response = HttpResponse(export_resp.content, content_type=export_mime_type)
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def drive_update_file(request, file_id):
    """
    Update a file in Google Drive by uploading new content.
    For Google Workspace files (Docs, Sheets, Slides), this converts the uploaded
    content to the appropriate Google Workspace format.
    
    Expects multipart/form-data with a 'file' field containing the file content.
    """
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

    # Get the uploaded file
    if 'file' not in request.FILES:
        return JsonResponse({"message": "No file provided"}, status=400)
    
    uploaded_file = request.FILES['file']
    file_content = uploaded_file.read()
    content_type = uploaded_file.content_type or 'application/octet-stream'

    # First get the current file metadata to check if it's a Google Workspace file
    metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType"
    metadata_resp = requests.get(metadata_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    
    if metadata_resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to get file metadata",
            "status": metadata_resp.status_code,
            "error": metadata_resp.text
        }, status=metadata_resp.status_code)
    
    metadata = metadata_resp.json()
    current_mime_type = metadata.get('mimeType', '')
    
    # Use Google Drive's update endpoint with media upload
    # For Google Workspace files, we need to specify the correct mimeType to convert
    update_url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type
    }
    
    # If uploading to a Google Doc, we need to convert the content
    # Google Drive will auto-convert based on the source MIME type
    update_resp = requests.patch(update_url, headers=headers, data=file_content, timeout=60)
    
    if update_resp.status_code not in [200, 204]:
        return JsonResponse({
            "message": "Failed to update file",
            "status": update_resp.status_code,
            "error": update_resp.text
        }, status=update_resp.status_code)
    
    # Get updated file metadata to return
    metadata_resp = requests.get(metadata_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if metadata_resp.status_code == 200:
        return JsonResponse(metadata_resp.json())
    else:
        return JsonResponse({"message": "File updated successfully", "id": file_id})


@csrf_exempt
@require_http_methods(["PATCH"])
def drive_rename_file(request, file_id):
    """
    Rename a file or folder in Google Drive.
    Request body (JSON):
        name: The new name for the file/folder
    """
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

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON body"}, status=400)

    new_name = body.get("name")
    if not new_name:
        return JsonResponse({"message": "name field is required"}, status=400)

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    resp = requests.patch(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={"name": new_name},
        timeout=20
    )

    if resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to rename file",
            "status": resp.status_code,
            "error": resp.text
        }, status=resp.status_code)

    return JsonResponse(resp.json())


@csrf_exempt
@require_http_methods(["DELETE"])
def drive_delete_file(request, file_id):
    """
    Delete a file or folder from Google Drive (moves to trash or permanently deletes).
    Query Parameters:
        permanent: If 'true', permanently deletes instead of trashing
    """
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

    permanent = request.GET.get('permanent', 'false').lower() == 'true'

    if permanent:
        # Permanently delete the file
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        resp = requests.delete(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20
        )
        if resp.status_code not in [200, 204]:
            return JsonResponse({
                "message": "Failed to delete file",
                "status": resp.status_code,
                "error": resp.text
            }, status=resp.status_code)
        return JsonResponse({"message": "File deleted permanently", "id": file_id})
    else:
        # Move to trash
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        resp = requests.patch(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"trashed": True},
            timeout=20
        )
        if resp.status_code != 200:
            return JsonResponse({
                "message": "Failed to trash file",
                "status": resp.status_code,
                "error": resp.text
            }, status=resp.status_code)
        return JsonResponse({"message": "File moved to trash", "id": file_id})


@csrf_exempt
@require_http_methods(["POST"])
def drive_star_file(request, file_id):
    """
    Star a file or folder in Google Drive.
    """
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

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    resp = requests.patch(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={"starred": True},
        timeout=20
    )

    if resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to star file",
            "status": resp.status_code,
            "error": resp.text
        }, status=resp.status_code)

    return JsonResponse({"message": "File starred", "id": file_id, "starred": True})


@csrf_exempt
@require_http_methods(["POST"])
def drive_unstar_file(request, file_id):
    """
    Unstar a file or folder in Google Drive.
    """
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

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    resp = requests.patch(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={"starred": False},
        timeout=20
    )

    if resp.status_code != 200:
        return JsonResponse({
            "message": "Failed to unstar file",
            "status": resp.status_code,
            "error": resp.text
        }, status=resp.status_code)

    return JsonResponse({"message": "File unstarred", "id": file_id, "starred": False})


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

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["GET"])
def get_site_visitor_info(request):
    """Retrieves site visitor information from the database."""
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        site_collection = db["site"]

        # Get query parameters for filtering
        limit = int(request.GET.get('limit', 100))  # Default to 100 records
        days = int(request.GET.get('days', 30))  # Default to last 30 days
        
        # Calculate date filter (including today)
        from datetime import datetime, timedelta
        # Use UTC time to match MongoDB storage
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = today_start - timedelta(days=days-1)
        
        # Query the database
        print(f"Main visitors query date range: {cutoff_date} to {datetime.utcnow()}")
        visitors = list(site_collection.find({
            "time": {"$gte": cutoff_date}
        }).sort("time", -1).limit(limit))
        print(f"Found {len(visitors)} visitors in date range")
        
        # Convert ObjectId to string for JSON serialization
        for visitor in visitors:
            visitor['_id'] = str(visitor['_id'])
            # Convert datetime to string
            if 'time' in visitor:
                visitor['time'] = visitor['time'].isoformat()
        
        # Get summary statistics
        total_visitors = site_collection.count_documents({})
        recent_visitors = site_collection.count_documents({"time": {"$gte": cutoff_date}})
        
        # Get country statistics
        country_stats = list(site_collection.aggregate([
            {"$group": {"_id": "$country", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        
        # Get city statistics
        city_stats = list(site_collection.aggregate([
            {"$group": {"_id": "$city", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        
        # Get hourly distribution for the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        hourly_stats = list(site_collection.aggregate([
            {"$match": {"time": {"$gte": yesterday}}},
            {"$group": {"_id": {"$hour": "$time"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        
        # Get daily visitor counts for the specified period (including today)
        try:
            # Use a date range that includes today by going back (days-1) days from today
            # This ensures we get the full period including today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily_cutoff = today_start - timedelta(days=days-1)
            print(f"Daily stats date range: {daily_cutoff} to {today_start}")
            print(f"Current time: {datetime.utcnow()}")
            
            daily_stats = list(site_collection.aggregate([
                {"$match": {"time": {"$gte": daily_cutoff}}},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$time"},
                        "month": {"$month": "$time"},
                        "day": {"$dayOfMonth": "$time"}
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}},
                {"$project": {
                    "_id": 0,
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {
                                "$dateFromParts": {
                                    "year": "$_id.year",
                                    "month": "$_id.month",
                                    "day": "$_id.day"
                                }
                            }
                        }
                    },
                    "count": 1
                }}
            ]))
            print(f"Daily stats query result: {daily_stats}")
            
            # Debug: Check if we have any visitors today
            today_str = today_start.strftime('%Y-%m-%d')
            today_visitors = [v for v in visitors if 'time' in v and v['time'].startswith(today_str)]
            print(f"Visitors found for today ({today_str}): {len(today_visitors)}")
            if today_visitors:
                print(f"Sample today visitor: {today_visitors[0]}")
        except Exception as e:
            print(f"Error in daily stats aggregation: {e}")
            # Fallback: create daily stats manually from visitors data (including today)
            daily_stats = []
            if visitors:
                from collections import defaultdict
                daily_counts = defaultdict(int)
                # Use the same date range logic as above
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                daily_cutoff = today_start - timedelta(days=days-1)
                
                for visitor in visitors:
                    if 'time' in visitor:
                        try:
                            # Parse the ISO string back to datetime
                            visitor_time = datetime.fromisoformat(visitor['time'].replace('Z', '+00:00'))
                            # Only count visitors from the daily cutoff date onwards
                            if visitor_time >= daily_cutoff:
                                date_key = visitor_time.strftime('%Y-%m-%d')
                                daily_counts[date_key] += 1
                        except Exception as parse_error:
                            print(f"Error parsing visitor time: {parse_error}")
                            continue
                
                # Convert to the expected format
                daily_stats = [
                    {"date": date, "count": count} 
                    for date, count in sorted(daily_counts.items())
                ]
            print(f"Fallback daily stats: {daily_stats}")
        
        response_data = {
            "result": "success",
            "visitors": visitors,
            "summary": {
                "total_visitors": total_visitors,
                "recent_visitors": recent_visitors,
                "period_days": days
            },
            "country_stats": country_stats,
            "city_stats": city_stats,
            "hourly_stats": hourly_stats,
            "daily_stats": daily_stats
        }
        
        return JsonResponse(response_data, safe=False)
        
    except Exception as e:
        print(f"Error retrieving visitor data: {e}")
        return JsonResponse({"error": "Failed to retrieve visitor data"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def browserbase_session(request):
	"""Authenticated proxy to create a Browserbase session and return an embeddable URL."""
	# Prefer auth from middleware if available
	username = getattr(request, 'username_from_token', None)
	if not username:
		# Fallback: validate bearer token manually
		auth_header = request.headers.get('Authorization')
		if auth_header and ' ' in auth_header:
			try:
				_type, token = auth_header.split(' ', 1)
				validated = AccessToken(token)
				username = validated.payload.get('username')
			except Exception:
				username = None
	# Final fallback: allow X-API-Key if configured and valid
	if not username:
		api_key_header = request.headers.get('X-API-Key')
		if not api_key_header or not validate_api_key(api_key_header):
			return JsonResponse({'message': 'Authentication required'}, status=401)

	# Read optional startUrl
	try:
		payload = json.loads(request.body or '{}')
	except Exception:
		payload = {}
	start_url = payload.get('startUrl') or 'https://news.google.com'

	# Call Browserbase API with server-side credentials
	api_key = os.environ.get('BROWSERBASE_API_KEY') or os.environ.get('BROWSERBASE_API_TOKEN')
	project_id = os.environ.get('BROWSERBASE_PROJECT_ID')
	if not api_key:
		return JsonResponse({ 'error': 'Browserbase API key not configured' }, status=500)

	try:
		# Browserbase API now only accepts projectId in the payload
		payload = {}
		if project_id:
			payload['projectId'] = project_id
		else:
			return JsonResponse({ 'error': 'Browserbase project ID not configured' }, status=500)

		endpoints = [
			'https://api.browserbase.com/v1/sessions',
		]
		header_modes = []
		# Mode A: x-bb-api-key header (correct format based on API response)
		mode_a = {
			'Content-Type': 'application/json',
			'x-bb-api-key': api_key,
		}
		header_modes.append(mode_a)
		# Mode B: Legacy headers as fallback
		mode_b = {
			'Content-Type': 'application/json',
			'Authorization': f'Bearer {api_key}',
			'X-API-Key': api_key,
			'x-api-key': api_key,
			'X-Browserbase-Api-Key': api_key,
			'x-browserbase-api-key': api_key,
		}
		if project_id:
			mode_b['x-browserbase-project-id'] = project_id
			mode_b['X-Browserbase-Project-Id'] = project_id
		header_modes.append(mode_b)
		# Mode C: Bearer only
		mode_c = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}' }
		if project_id:
			mode_c['x-browserbase-project-id'] = project_id
		header_modes.append(mode_c)

		last_resp = None
		for url in endpoints:
			for hdrs in header_modes:
				resp = requests.post(url, json=payload, headers=hdrs, timeout=30)
				last_resp = resp
				if 200 <= resp.status_code < 300:
					try:
						data = resp.json()
						session_id = data.get('id')
						
						# Fetch debug URLs for the session
						if session_id:
							debug_url = f'https://api.browserbase.com/v1/sessions/{session_id}/debug'
							debug_resp = requests.get(debug_url, headers=hdrs, timeout=10)
							if debug_resp.status_code == 200:
								debug_data = debug_resp.json()
								# Map debuggerFullscreenUrl to embedUrl/viewerUrl
								if 'debuggerFullscreenUrl' in debug_data:
									data['embedUrl'] = debug_data['debuggerFullscreenUrl']
									data['viewerUrl'] = debug_data['debuggerFullscreenUrl']
								elif 'debuggerUrl' in debug_data:
									data['embedUrl'] = debug_data['debuggerUrl']
									data['viewerUrl'] = debug_data['debuggerUrl']
					except Exception:
						data = {}
					return JsonResponse(data, status=200)
				# If unauthorized or forbidden, try next mode/endpoint
				if resp.status_code in (401, 403):
					continue
				# Other errors: break to return
				break
		# If we reach here, return last response details
		if last_resp is not None:
			return JsonResponse({ 'error': last_resp.text or f'HTTP {last_resp.status_code}' }, status=last_resp.status_code)
		return JsonResponse({ 'error': 'Unknown error contacting Browserbase' }, status=502)
	except Exception as e:
		return JsonResponse({ 'error': str(e) }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_login_analytics(request):
	"""Retrieves login analytics from the database."""
	try:
		# MongoDB connection
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		login_collection = db["user_logins"]
		
		# Get query parameters for filtering
		limit = int(request.GET.get('limit', 100))  # Default to 100 records
		days = int(request.GET.get('days', 30))  # Default to last 30 days
		
		# Calculate date filter (including today)
		from datetime import datetime, timedelta
		today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
		cutoff_date = today_start - timedelta(days=days-1)
		
		logins = list(login_collection.find({
			"timestamp": {"$gte": cutoff_date}
		}).sort("timestamp", -1).limit(limit))
		
		# Convert ObjectId to string for JSON serialization
		for login in logins:
			login['_id'] = str(login['_id'])
			# Convert datetime to string
			if 'timestamp' in login:
				login['timestamp'] = login['timestamp'].isoformat()
		
		# Get summary statistics
		total_logins = login_collection.count_documents({})
		recent_logins = login_collection.count_documents({"timestamp": {"$gte": cutoff_date}})
		
		# Get auth method statistics
		auth_method_stats = list(login_collection.aggregate([
			{"$match": {"timestamp": {"$gte": cutoff_date}}},
			{"$group": {"_id": "$auth_method", "count": {"$sum": 1}}},
			{"$sort": {"count": -1}}
		]))
		
		# Get hourly distribution for the last 24 hours
		yesterday = datetime.utcnow() - timedelta(days=1)
		hourly_stats = list(login_collection.aggregate([
			{"$match": {"timestamp": {"$gte": yesterday}}},
			{"$group": {"_id": {"$hour": "$timestamp"}, "count": {"$sum": 1}}},
			{"$sort": {"_id": 1}}
		]))
		
		# Get daily login counts for the specified period (including today)
		try:
			daily_stats = list(login_collection.aggregate([
				{"$match": {"timestamp": {"$gte": cutoff_date}}},
				{"$group": {
					"_id": {
						"year": {"$year": "$timestamp"},
						"month": {"$month": "$timestamp"},
						"day": {"$dayOfMonth": "$timestamp"}
					},
					"count": {"$sum": 1}
				}},
				{"$sort": {"_id": 1}},
				{"$project": {
					"_id": 0,
					"date": {
						"$dateToString": {
							"format": "%Y-%m-%d",
							"date": {
								"$dateFromParts": {
									"year": "$_id.year",
									"month": "$_id.month",
									"day": "$_id.day"
								}
							}
						}
					},
					"count": 1
				}}
			]))
		except Exception as e:
			daily_stats = []
		
		# Get top users by login count
		top_users_stats = list(login_collection.aggregate([
			{"$match": {"timestamp": {"$gte": cutoff_date}}},
			{"$group": {"_id": "$username", "count": {"$sum": 1}}},
			{"$sort": {"count": -1}},
			{"$limit": 10}
		]))
		
		response_data = {
			"result": "success",
			"logins": logins,
			"summary": {
				"total_logins": total_logins,
				"recent_logins": recent_logins,
				"period_days": days
			},
			"auth_method_stats": auth_method_stats,
			"hourly_stats": hourly_stats,
			"daily_stats": daily_stats,
			"top_users_stats": top_users_stats
		}
		
		return JsonResponse(response_data, safe=False)
		
	except Exception as e:
		print(f"Error retrieving login analytics: {e}")
		return JsonResponse({"error": "Failed to retrieve login analytics"}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_google_scopes_analytics(request):
	"""Retrieves Google OAuth scopes analytics from the database."""
	try:
		# MongoDB connection
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		# Get all users with Google OAuth credentials
		users_with_google = list(user_collection.find(
			{"google_drive_credentials": {"$exists": True}},
			{"google_drive_credentials.scopes": 1, "username": 1, "email": 1}
		))
		
		# Analyze scope usage
		scope_usage = {}
		total_google_users = len(users_with_google)
		users_with_scopes = []
		
		for user in users_with_google:
			user_id = str(user.get("_id"))
			username = user.get("username", "")
			email = user.get("email", "")
			credentials = user.get("google_drive_credentials", {})
			scopes = credentials.get("scopes", [])
			
			if scopes:
				users_with_scopes.append({
					"user_id": user_id,
					"username": username,
					"email": email,
					"scopes": scopes,
					"scope_count": len(scopes)
				})
				
				# Count each scope
				for scope in scopes:
					if scope in scope_usage:
						scope_usage[scope] += 1
					else:
						scope_usage[scope] = 1
		
		# Convert to sorted list
		scope_stats = [
			{"scope": scope, "count": count, "percentage": round((count / total_google_users) * 100, 1)}
			for scope, count in sorted(scope_usage.items(), key=lambda x: x[1], reverse=True)
		]
		
		# Get scope categories
		scope_categories = {}
		for scope in scope_usage.keys():
			if 'userinfo' in scope:
				category = 'User Info'
			elif 'gmail' in scope:
				category = 'Gmail'
			elif 'drive' in scope:
				category = 'Google Drive'
			elif 'calendar' in scope:
				category = 'Google Calendar'
			elif 'contacts' in scope:
				category = 'Contacts'
			else:
				category = 'Other'
			
			if category in scope_categories:
				scope_categories[category] += scope_usage[scope]
			else:
				scope_categories[category] = scope_usage[scope]
		
		category_stats = [
			{"category": category, "count": count}
			for category, count in sorted(scope_categories.items(), key=lambda x: x[1], reverse=True)
		]
		
		# Get distribution of scope counts per user
		scope_count_distribution = {}
		for user in users_with_scopes:
			count = user["scope_count"]
			if count in scope_count_distribution:
				scope_count_distribution[count] += 1
			else:
				scope_count_distribution[count] = 1
		
		distribution_stats = [
			{"scope_count": count, "user_count": user_count}
			for count, user_count in sorted(scope_count_distribution.items())
		]
		
		response_data = {
			"result": "success",
			"summary": {
				"total_google_users": total_google_users,
				"users_with_scopes": len(users_with_scopes),
				"unique_scopes": len(scope_usage),
				"most_common_scope": scope_stats[0]["scope"] if scope_stats else None,
				"average_scopes_per_user": round(sum(user["scope_count"] for user in users_with_scopes) / len(users_with_scopes), 1) if users_with_scopes else 0
			},
			"scope_stats": scope_stats,
			"category_stats": category_stats,
			"distribution_stats": distribution_stats,
			"users_with_scopes": users_with_scopes[:20]  # Limit to first 20 for performance
		}
		
		return JsonResponse(response_data, safe=False)
		
	except Exception as e:
		print(f"Error retrieving Google scopes analytics: {e}")
		return JsonResponse({"error": "Failed to retrieve Google scopes analytics"}, status=500)


# X API endpoints

# OAuth2 (PKCE) helper functions for X API
def _base64url_encode(raw_bytes: bytes) -> str:
	return base64.urlsafe_b64encode(raw_bytes).rstrip(b'=').decode('utf-8')

def _generate_code_verifier() -> str:
	# 64-char unpadded URL-safe string
	random_bytes = os.urandom(64)
	return _base64url_encode(random_bytes)[:64]

def _code_challenge_from_verifier(verifier: str) -> str:
	digest = hashlib.sha256(verifier.encode('utf-8')).digest()
	return _base64url_encode(digest)

def _get_user_doc(username: str):
	uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
	client = MongoClient(uri)
	db = client["NeuraNet"]
	user_collection = db["users"]
	return user_collection.find_one({"username": username}), user_collection

def _now_utc_iso() -> str:
	return datetime.utcnow().isoformat()

def _ensure_oauth2_token_fresh(user_doc: dict, user_collection, username: str) -> tuple[str | None, dict | None]:
	"""Return valid access_token, updated_oauth2 dict if refreshed. Handles refresh if expired."""
	oauth2 = (user_doc or {}).get('x_api_oauth2') or {}
	access_token = oauth2.get('access_token')
	refresh_token = oauth2.get('refresh_token')
	expires_at = oauth2.get('expires_at')
	client_id = os.environ.get('X_OAUTH2_CLIENT_ID')
	client_secret = os.environ.get('X_OAUTH2_CLIENT_SECRET')
	if not access_token:
		return None, None
	# If no expiry, assume valid
	try:
		is_expired = False
		if expires_at:
			exp_dt = datetime.fromisoformat(expires_at)
			is_expired = exp_dt <= datetime.utcnow()
	except Exception:
		is_expired = False
	if not is_expired:
		return access_token, None
	# Refresh if we can
	if not refresh_token:
		return None, None
	try:
		data = {
			'grant_type': 'refresh_token',
			'refresh_token': refresh_token,
		}
		if client_id:
			data['client_id'] = client_id
		# Some providers require client_secret; include when present
		if client_secret:
			data['client_secret'] = client_secret
		resp = requests.post(
			"https://api.twitter.com/2/oauth2/token",
			data=data,
			headers={'Content-Type': 'application/x-www-form-urlencoded'},
			timeout=15
		)
		if resp.status_code != 200:
			return None, None
		payload = resp.json() or {}
		new_access = payload.get('access_token')
		new_refresh = payload.get('refresh_token') or refresh_token
		expires_in = payload.get('expires_in')
		scope = payload.get('scope') or oauth2.get('scope')
		token_type = payload.get('token_type') or oauth2.get('token_type')
		new_expires_at = None
		if isinstance(expires_in, int):
			new_expires_at = (datetime.utcnow() + timedelta(seconds=max(expires_in - 60, 0))).isoformat()
		if new_access:
			updated = {
				'access_token': new_access,
				'refresh_token': new_refresh,
				'expires_at': new_expires_at or oauth2.get('expires_at'),
				'scope': scope,
				'token_type': token_type,
				'user_id': oauth2.get('user_id'),
				'username': oauth2.get('username')
			}
			user_collection.update_one({"username": username}, {"$set": {"x_api_oauth2": updated}})
			return new_access, updated
		return None, None
	except Exception:
		return None, None
@csrf_exempt
@require_http_methods(["GET"])
def x_api_user_info(request):
	"""Get X (Twitter) user information by username or user ID."""
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

		# Get query parameters
		username_param = request.GET.get('username')
		user_id_param = request.GET.get('user_id')
		
		if not username_param and not user_id_param:
			return JsonResponse({'error': 'Either username or user_id parameter is required'}, status=400)

		# Get X API credentials from environment
		x_api_key = os.environ.get('X_API_KEY')
		x_api_secret = os.environ.get('X_API_SECRET')
		x_bearer_token = os.environ.get('X_BEARER_TOKEN')
		
		if not x_bearer_token:
			return JsonResponse({'error': 'X API credentials not configured'}, status=500)

		# Build X API URL
		if username_param:
			url = f"https://api.twitter.com/2/users/by/username/{username_param}"
		else:
			url = f"https://api.twitter.com/2/users/{user_id_param}"
		
		# Add user fields (include protected for visibility)
		url += "?user.fields=id,name,username,description,profile_image_url,public_metrics,verified,created_at,protected"

		# Make request to X API
		headers = {
			'Authorization': f'Bearer {x_bearer_token}',
			'Content-Type': 'application/json'
		}
		
		response = requests.get(url, headers=headers, timeout=30)
		
		if response.status_code == 200:
			data = response.json()
			return JsonResponse(data, safe=False)
		else:
			rate_remaining = response.headers.get('x-rate-limit-remaining')
			rate_reset = response.headers.get('x-rate-limit-reset')
			return JsonResponse({
				'error': f'X API error: {response.status_code} - {response.text}',
				'rate_limit_remaining': rate_remaining,
				'rate_limit_reset': rate_reset
			}, status=response.status_code)
			
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def x_api_oauth2_initiate(request):
	"""Start OAuth2 PKCE flow: returns auth_url for client redirect."""
	try:
		# Auth user
		auth_header = request.headers.get('Authorization')
		if not auth_header or ' ' not in auth_header:
			return JsonResponse({'message': 'Authentication required'}, status=401)
		auth_type, token = auth_header.split(' ', 1)
		if auth_type.lower() != 'bearer':
			return JsonResponse({'message': 'Invalid authentication type'}, status=401)
		validated = AccessToken(token)
		username = validated.payload.get('username')
		if not username:
			return JsonResponse({'message': 'Invalid token'}, status=401)

		client_id = os.environ.get('X_OAUTH2_CLIENT_ID')
		redirect_uri = os.environ.get('X_OAUTH2_REDIRECT_URI') or request.POST.get('redirect_uri') or request.GET.get('redirect_uri')
		scope = os.environ.get('X_OAUTH2_SCOPE') or 'tweet.read users.read offline.access'
		if not client_id or not redirect_uri:
			return JsonResponse({'error': 'OAuth2 not configured (client_id/redirect_uri)'}, status=500)

		state = _base64url_encode(os.urandom(24))
		verifier = _generate_code_verifier()
		challenge = _code_challenge_from_verifier(verifier)

		# Persist state + verifier for user
		user_doc, user_collection = _get_user_doc(username)
		user_collection.update_one(
			{"username": username},
			{"$set": {"x_api_oauth2_state": {"state": state, "code_verifier": verifier, "created_at": _now_utc_iso()}}},
			upsert=True
		)

		authorize_url = "https://twitter.com/i/oauth2/authorize"
		params = {
			'response_type': 'code',
			'client_id': client_id,
			'redirect_uri': redirect_uri,
			'scope': scope,
			'state': state,
			'code_challenge': challenge,
			'code_challenge_method': 'S256'
		}
		return JsonResponse({'auth_url': f"{authorize_url}?{urllib.parse.urlencode(params)}"})
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def x_api_oauth2_callback(request):
	"""Exchange code for tokens, store in Mongo under x_api_oauth2."""
	try:
		# Auth user
		auth_header = request.headers.get('Authorization')
		if not auth_header or ' ' not in auth_header:
			return JsonResponse({'message': 'Authentication required'}, status=401)
		auth_type, token = auth_header.split(' ', 1)
		if auth_type.lower() != 'bearer':
			return JsonResponse({'message': 'Invalid authentication type'}, status=401)
		validated = AccessToken(token)
		username = validated.payload.get('username')
		if not username:
			return JsonResponse({'message': 'Invalid token'}, status=401)

		code = request.POST.get('code') or request.GET.get('code')
		state = request.POST.get('state') or request.GET.get('state')
		if not code or not state:
			return JsonResponse({'error': 'Missing code/state'}, status=400)

		client_id = os.environ.get('X_OAUTH2_CLIENT_ID')
		client_secret = os.environ.get('X_OAUTH2_CLIENT_SECRET')
		redirect_uri = os.environ.get('X_OAUTH2_REDIRECT_URI') or request.POST.get('redirect_uri') or request.GET.get('redirect_uri')
		if not client_id or not redirect_uri:
			return JsonResponse({'error': 'OAuth2 not configured (client_id/redirect_uri)'}, status=500)

		user_doc, user_collection = _get_user_doc(username)
		state_doc = (user_doc or {}).get('x_api_oauth2_state') or {}
		if state_doc.get('state') != state:
			return JsonResponse({'error': 'Invalid state'}, status=400)
		verifier = state_doc.get('code_verifier')
		if not verifier:
			return JsonResponse({'error': 'Missing code_verifier'}, status=400)

		data = {
			'grant_type': 'authorization_code',
			'code': code,
			'redirect_uri': redirect_uri,
			'code_verifier': verifier,
			'client_id': client_id,
		}
		if client_secret:
			data['client_secret'] = client_secret
		resp = requests.post(
			"https://api.twitter.com/2/oauth2/token",
			data=data,
			headers={'Content-Type': 'application/x-www-form-urlencoded'},
			timeout=15
		)
		if resp.status_code != 200:
			return JsonResponse({'error': f'Token exchange failed: {resp.status_code} - {resp.text}'}, status=resp.status_code)
		payload = resp.json() or {}
		access_token = payload.get('access_token')
		refresh_token = payload.get('refresh_token')
		expires_in = payload.get('expires_in')
		scope = payload.get('scope')
		token_type = payload.get('token_type')
		expires_at = None
		if isinstance(expires_in, int):
			expires_at = (datetime.utcnow() + timedelta(seconds=max(expires_in - 60, 0))).isoformat()

		# Resolve user id/username via v2 me endpoint
		resolved_user_id = None
		resolved_username = None
		if access_token:
			me_resp = requests.get(
				"https://api.twitter.com/2/users/me?user.fields=id,username,name",
				headers={'Authorization': f'Bearer {access_token}'},
				timeout=10
			)
			if me_resp.status_code == 200:
				me = me_resp.json() or {}
				ud = me.get('data') or {}
				resolved_user_id = ud.get('id')
				resolved_username = ud.get('username')

		user_collection.update_one(
			{"username": username},
			{"$set": {
				"x_api_oauth2": {
					"access_token": access_token,
					"refresh_token": refresh_token,
					"expires_at": expires_at,
					"scope": scope,
					"token_type": token_type,
					"user_id": resolved_user_id,
					"username": resolved_username,
				},
				"x_api_oauth2_state": None
			}},
			upsert=True
		)
		return JsonResponse({'success': True, 'user_id': resolved_user_id, 'username': resolved_username})
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def x_api_oauth2_disconnect(request):
	"""Clear stored OAuth2 credentials for the authenticated user."""
	try:
		auth_header = request.headers.get('Authorization')
		if not auth_header or ' ' not in auth_header:
			return JsonResponse({'message': 'Authentication required'}, status=401)
		auth_type, token = auth_header.split(' ', 1)
		if auth_type.lower() != 'bearer':
			return JsonResponse({'message': 'Invalid authentication type'}, status=401)
		validated = AccessToken(token)
		username = validated.payload.get('username')
		if not username:
			return JsonResponse({'message': 'Invalid token'}, status=401)

		user_doc, user_collection = _get_user_doc(username)
		user_collection.update_one({"username": username}, {"$unset": {"x_api_oauth2": "", "x_api_oauth2_state": ""}})
		return JsonResponse({'success': True})
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)
@csrf_exempt
@require_http_methods(["GET"])
def x_api_user_tweets(request):
	"""Get recent tweets from an X (Twitter) user."""
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

		# Get query parameters
		username_param = request.GET.get('username')
		user_id_param = request.GET.get('user_id')
		try:
			max_results = int(request.GET.get('max_results', 10))
		except (TypeError, ValueError):
			return JsonResponse({'error': 'max_results must be an integer'}, status=400)
		exclude_retweets = request.GET.get('exclude_retweets', 'false').lower() == 'true'
		exclude_replies = request.GET.get('exclude_replies', 'false').lower() == 'true'
		
		if not username_param and not user_id_param:
			return JsonResponse({'error': 'Either username or user_id parameter is required'}, status=400)

		# Get X API credentials from environment
		x_bearer_token = os.environ.get('X_BEARER_TOKEN')
		use_app_bearer = request.GET.get('use_app_bearer', 'false').lower() == 'true'
		
		# OAuth2 user-bearer preferred if present
		user_doc = None
		user_collection = None
		try:
			uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
			client = MongoClient(uri)
			db = client["NeuraNet"]
			user_collection = db["users"]
			user_doc = user_collection.find_one({"username": username})
		except Exception:
			user_doc = None

		if (not use_app_bearer) and user_doc and user_doc.get('x_api_oauth2', {}).get('access_token'):
			user_access_token, updated = _ensure_oauth2_token_fresh(user_doc, user_collection, username)
			if user_access_token:
				# Resolve user_id if needed using user bearer
				resolved_user_id = user_id_param
				if username_param and not resolved_user_id:
					try:
						user_url = f"https://api.twitter.com/2/users/by/username/{username_param}?user.fields=id,username"
						resp = requests.get(user_url, headers={'Authorization': f'Bearer {user_access_token}'}, timeout=15)
						if resp.status_code != 200:
							return JsonResponse({'error': f'X API error getting user: {resp.status_code}'}, status=resp.status_code)
						ud = resp.json() or {}
						resolved_user_id = (ud.get('data') or {}).get('id')
						if not resolved_user_id:
							return JsonResponse({'error': 'User not found'}, status=404)
					except requests.exceptions.RequestException as e:
						return JsonResponse({'error': f'Upstream X API error (user lookup v2 user-bearer): {str(e)}'}, status=502)

				# Build v2 tweets request with user bearer
				url = f"https://api.twitter.com/2/users/{resolved_user_id}/tweets"
				params = {
					'max_results': min(max_results, 100),
					'tweet.fields': 'id,text,created_at,public_metrics,entities,referenced_tweets'
				}
				if exclude_retweets:
					params['exclude'] = 'retweets'
				if exclude_replies:
					params['exclude'] = params.get('exclude', '') + ',replies' if params.get('exclude') else 'replies'
				try:
					resp = requests.get(url, headers={'Authorization': f'Bearer {user_access_token}'}, params=params, timeout=30)
				except requests.exceptions.RequestException as e:
					return JsonResponse({'error': f'Upstream X API error (tweets v2 user-bearer): {str(e)}'}, status=502)
				if resp.status_code == 200:
					return JsonResponse(resp.json(), safe=False)
				# If unauthorized with user token, attempt app-bearer fallback if configured
				if resp.status_code in (401, 403) and x_bearer_token:
					pass
				else:
					return JsonResponse({'error': f'X API error: {resp.status_code} - {resp.text}'}, status=resp.status_code)

		# Try to use per-user OAuth1 credentials next (legacy)
		user_x_credentials = (user_doc or {}).get('x_api_credentials') if user_doc else None
		try:
			uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
			client = MongoClient(uri)
			db = client["NeuraNet"]
			user_collection = db["users"]
			user_doc = user_collection.find_one({"username": username})
			if user_doc:
				user_x_credentials = user_doc.get('x_api_credentials', {})
		except Exception:
			user_x_credentials = None

		# If user has OAuth1 credentials, use v1.1 timeline with user context
		if (not use_app_bearer) and user_x_credentials and user_x_credentials.get('access_token') and user_x_credentials.get('access_token_secret'):
			try:
				from requests_oauthlib import OAuth1Session
				x_api_key = os.environ.get('X_API_KEY')
				x_api_secret = os.environ.get('X_API_SECRET')
				if not x_api_key or not x_api_secret:
					return JsonResponse({'error': 'X API consumer keys not configured'}, status=500)

				oauth = OAuth1Session(
					x_api_key,
					client_secret=x_api_secret,
					resource_owner_key=user_x_credentials.get('access_token'),
					resource_owner_secret=user_x_credentials.get('access_token_secret')
				)

				# Resolve user_id if only username was provided
				resolved_user_id = user_id_param
				if username_param and not resolved_user_id:
					try:
						lookup_url = "https://api.twitter.com/1.1/users/show.json"
						lu_resp = oauth.get(lookup_url, params={'screen_name': username_param}, timeout=30)
						if lu_resp.status_code != 200:
							return JsonResponse({'error': f'X API error getting user (v1.1): {lu_resp.status_code}'}, status=lu_resp.status_code)
						ud = lu_resp.json() or {}
						resolved_user_id = ud.get('id_str') or (str(ud.get('id')) if ud.get('id') is not None else None)
						if not resolved_user_id:
							return JsonResponse({'error': 'User not found'}, status=404)
					except requests.exceptions.RequestException as e:
						return JsonResponse({'error': f'Upstream X API error (user lookup v1.1): {str(e)}'}, status=502)

				# Build v1.1 timeline params
				timeline_url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
				params_v11 = {
					'user_id': resolved_user_id or user_id_param,
					'count': min(max_results, 200),
					'tweet_mode': 'extended'
				}
				if exclude_retweets:
					params_v11['include_rts'] = 'false'
				if exclude_replies:
					params_v11['exclude_replies'] = 'true'

				try:
					resp = oauth.get(timeline_url, params=params_v11, timeout=30)
				except requests.exceptions.RequestException as e:
					return JsonResponse({'error': f'Upstream X API error (tweets v1.1): {str(e)}'}, status=502)

				if resp.status_code == 200:
					data = resp.json()
					return JsonResponse(data, safe=False)
				else:
					# If app bearer is available, fall through to v2 implementation below
					if not x_bearer_token:
						return JsonResponse({'error': f'X API error (v1.1): {resp.status_code} - {resp.text}'}, status=resp.status_code)
			except Exception as e:
				# Fall through to app-level bearer if available
				pass

		# If no per-user credentials (or explicitly forced), require app-level bearer for v2
		if not x_bearer_token:
			return JsonResponse({'error': 'No X user credentials connected and app bearer token not configured'}, status=400)

		# First get user ID if username provided
		user_id = user_id_param
		if username_param:
			user_url = f"https://api.twitter.com/2/users/by/username/{username_param}"
			headers = {
				'Authorization': f'Bearer {x_bearer_token}',
				'Content-Type': 'application/json'
			}
			
			try:
				user_response = requests.get(user_url, headers=headers, timeout=30)
			except requests.exceptions.RequestException as e:
				return JsonResponse({'error': f'Upstream X API error (user lookup): {str(e)}'}, status=502)
			if user_response.status_code != 200:
				return JsonResponse({'error': f'X API error getting user: {user_response.status_code}'}, status=user_response.status_code)
			
			user_data = user_response.json()
			user_id = user_data.get('data', {}).get('id')
			if not user_id:
				return JsonResponse({'error': 'User not found'}, status=404)

		# Build tweets URL
		url = f"https://api.twitter.com/2/users/{user_id}/tweets"
		
		# Add parameters
		params = {
			'max_results': min(max_results, 100),
			'tweet.fields': 'id,text,created_at,public_metrics,entities,referenced_tweets'
		}
		
		if exclude_retweets:
			params['exclude'] = 'retweets'
		if exclude_replies:
			params['exclude'] = params.get('exclude', '') + ',replies' if params.get('exclude') else 'replies'

		# Make request to X API
		headers = {
			'Authorization': f'Bearer {x_bearer_token}',
			'Content-Type': 'application/json'
		}

		try:
			response = requests.get(url, headers=headers, params=params, timeout=30)
		except requests.exceptions.RequestException as e:
			return JsonResponse({'error': f'Upstream X API error (tweets): {str(e)}'}, status=502)
		
		if response.status_code == 200:
			data = response.json()
			return JsonResponse(data, safe=False)
		else:
			rate_remaining = response.headers.get('x-rate-limit-remaining')
			rate_reset = response.headers.get('x-rate-limit-reset')
			return JsonResponse({
				'error': f'X API error: {response.status_code} - {response.text}',
				'rate_limit_remaining': rate_remaining,
				'rate_limit_reset': rate_reset
			}, status=response.status_code)
			
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def x_api_search_tweets(request):
	"""Search for tweets using X (Twitter) search API."""
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

		# Get query parameters
		query = request.GET.get('query')
		max_results = int(request.GET.get('max_results', 10))
		language = request.GET.get('language', 'en')
		result_type = request.GET.get('result_type', 'recent')
		
		if not query:
			return JsonResponse({'error': 'Query parameter is required'}, status=400)

		# Get X API credentials from environment
		x_bearer_token = os.environ.get('X_BEARER_TOKEN')
		# Normalize bearer if URL-encoded in env
		if x_bearer_token and '%' in x_bearer_token:
			try:
				x_bearer_token = urllib.parse.unquote(x_bearer_token)
			except Exception:
				pass
		
		if not x_bearer_token:
			return JsonResponse({'error': 'X API credentials not configured'}, status=500)

		# Build search URL
		url = "https://api.twitter.com/2/tweets/search/recent"
		
		# Add parameters
		params = {
			'query': query,
			'max_results': min(max_results, 100),
			'tweet.fields': 'id,text,created_at,public_metrics,entities,author_id',
			'user.fields': 'id,name,username,profile_image_url,verified',
			'expansions': 'author_id'
		}
		
		if language != 'en':
			params['lang'] = language

		# Make request to X API
		headers = {
			'Authorization': f'Bearer {x_bearer_token}',
			'Content-Type': 'application/json'
		}
		
		response = requests.get(url, headers=headers, params=params, timeout=30)
		
		if response.status_code == 200:
			data = response.json()
			return JsonResponse(data, safe=False)
		else:
			return JsonResponse({'error': f'X API error: {response.status_code} - {response.text}'}, status=response.status_code)
			
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def x_api_trending_topics(request):
	"""Get trending topics on X (Twitter) for a specific location."""
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

		# Get query parameters
		woeid = request.GET.get('woeid', '1')  # Default to worldwide (1)
		count = int(request.GET.get('count', 10))

		# Get X API credentials from environment
		x_api_key = os.environ.get('X_API_KEY')
		x_api_secret = os.environ.get('X_API_SECRET')
		
		if not x_api_key or not x_api_secret:
			return JsonResponse({'error': 'X API credentials not configured'}, status=500)

		# Build trending topics URL (using v1.1 API for trends)
		url = f"https://api.twitter.com/1.1/trends/place.json"
		
		# Add parameters
		params = {
			'id': woeid,
			'count': min(count, 50)
		}

		# Create OAuth1 session for v1.1 API
		from requests_oauthlib import OAuth1Session
		
		oauth = OAuth1Session(
			x_api_key,
			client_secret=x_api_secret,
			resource_owner_key="",  # Not needed for app-only auth
			resource_owner_secret=""  # Not needed for app-only auth
		)
		
		response = oauth.get(url, params=params, timeout=30)
		
		if response.status_code == 200:
			data = response.json()
			return JsonResponse(data, safe=False)
		else:
			return JsonResponse({'error': f'X API error: {response.status_code} - {response.text}'}, status=response.status_code)
			
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def x_api_post_tweet(request):
	"""Post a new tweet to X (Twitter)."""
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

		# Parse request body
		data = json.loads(request.body) if request.body else {}
		text = data.get('text')
		reply_to_tweet_id = data.get('reply_to_tweet_id')
		media_ids = data.get('media_ids', [])
		
		if not text:
			return JsonResponse({'error': 'Text parameter is required'}, status=400)

		# Get user document from MongoDB to get stored X credentials
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		# Find the user by username
		user = user_collection.find_one({"username": username})
		if not user:
			return JsonResponse({'message': 'User not found'}, status=404)
		
		# Get user's stored X API credentials
		x_credentials = user.get('x_api_credentials', {})
		if not x_credentials or not x_credentials.get('access_token'):
			return JsonResponse({'error': 'No X account connected. Please connect your X account in settings.'}, status=400)
		
		# Get X API app credentials from environment
		x_api_key = os.environ.get('X_API_KEY')
		x_api_secret = os.environ.get('X_API_SECRET')
		
		if not x_api_key or not x_api_secret:
			return JsonResponse({'error': 'X API credentials not configured'}, status=500)

		# Build tweet URL
		url = "https://api.twitter.com/2/tweets"
		
		# Build payload
		payload = {
			'text': text
		}
		
		if reply_to_tweet_id:
			payload['reply'] = {
				'in_reply_to_tweet_id': reply_to_tweet_id
			}
		
		if media_ids and len(media_ids) > 0:
			payload['media'] = {
				'media_ids': media_ids
			}

		# Create OAuth1 session for posting using user's stored credentials
		from requests_oauthlib import OAuth1Session
		
		oauth = OAuth1Session(
			x_api_key,
			client_secret=x_api_secret,
			resource_owner_key=x_credentials.get('access_token'),
			resource_owner_secret=x_credentials.get('access_token_secret')
		)
		
		response = oauth.post(url, json=payload, timeout=30)
		
		if response.status_code == 201:
			data = response.json()
			return JsonResponse(data, safe=False)
		else:
			return JsonResponse({'error': f'X API error: {response.status_code} - {response.text}'}, status=response.status_code)
			
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# X API Connection Management
@csrf_exempt
@require_http_methods(["GET"])
def x_api_connection_status(request):
	"""Get the current X API connection status for the authenticated user."""
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

		# Get user document from MongoDB
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		# Find the user by username
		user = user_collection.find_one({"username": username})
		if not user:
			return JsonResponse({'message': 'User not found'}, status=404)
		
		# Prefer OAuth2 connection status
		u_oauth2 = user.get('x_api_oauth2') or {}
		if u_oauth2.get('access_token'):
			access_token, updated = _ensure_oauth2_token_fresh(user, user_collection, username)
			if access_token:
				try:
					me_resp = requests.get("https://api.twitter.com/2/users/me?user.fields=id,username,protected", headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
					if me_resp.status_code == 200:
						ud = (me_resp.json() or {}).get('data') or {}
						return JsonResponse({'connected': True, 'username': ud.get('username'), 'user_id': ud.get('id'), 'protected': ud.get('protected', False), 'last_verified': datetime.utcnow().isoformat(), 'auth': 'oauth2'})
					else:
						# Treat as disconnected if token invalid
						return JsonResponse({'connected': False, 'error': f'oauth2 verify failed: {me_resp.status_code}'})
				except Exception as e:
					return JsonResponse({'connected': False, 'error': f'oauth2 verify error: {str(e)}'})

		# Fallback to legacy OAuth1
		x_credentials = user.get('x_api_credentials', {})
		if not x_credentials or not x_credentials.get('access_token'):
			return JsonResponse({'connected': False, 'username': None, 'user_id': None, 'last_verified': None})
		try:
			x_api_key = os.environ.get('X_API_KEY')
			x_api_secret = os.environ.get('X_API_SECRET')
			if not x_api_key or not x_api_secret:
				return JsonResponse({'error': 'X API credentials not configured'}, status=500)
			from requests_oauthlib import OAuth1Session
			oauth = OAuth1Session(x_api_key, client_secret=x_api_secret, resource_owner_key=x_credentials.get('access_token'), resource_owner_secret=x_credentials.get('access_token_secret'))
			verify_url = "https://api.twitter.com/1.1/account/verify_credentials.json"
			resp = oauth.get(verify_url, timeout=10)
			if resp.status_code == 200:
				ud = resp.json() or {}
				return JsonResponse({'connected': True, 'username': ud.get('screen_name') or ud.get('username'), 'user_id': str(ud.get('id')) if ud.get('id') is not None else x_credentials.get('user_id'), 'last_verified': datetime.utcnow().isoformat(), 'auth': 'oauth1'})
			user_collection.update_one({"username": username}, {"$unset": {"x_api_credentials": ""}})
			return JsonResponse({'connected': False, 'username': None, 'user_id': None, 'last_verified': None, 'error': f'Connection verification failed: HTTP {resp.status_code}'})
		except Exception as e:
			return JsonResponse({'connected': False, 'username': None, 'user_id': None, 'last_verified': None, 'error': f'Connection test failed: {str(e)}'})
			
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def x_api_initiate_oauth(request):
	"""Initiate X OAuth flow for user connection."""
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

		# Parse request body
		data = json.loads(request.body) if request.body else {}
		callback_url = data.get('callback_url')
		
		if not callback_url:
			return JsonResponse({'error': 'Callback URL is required'}, status=400)

		# Get X API credentials from environment
		x_api_key = os.environ.get('X_API_KEY')
		x_api_secret = os.environ.get('X_API_SECRET')
		
		if not x_api_key or not x_api_secret:
			return JsonResponse({'error': 'X API credentials not configured'}, status=500)

		# Create OAuth1 session for authorization
		from requests_oauthlib import OAuth1Session
		
		oauth = OAuth1Session(
			x_api_key,
			client_secret=x_api_secret,
			callback_uri=callback_url
		)
		
		# Get request token
		request_token_url = "https://api.twitter.com/oauth/request_token"
		oauth_response = oauth.fetch_request_token(request_token_url)
		
		# Store the request token temporarily (in production, use Redis or similar)
		# For now, we'll store it in the user document
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		user_collection.update_one(
			{"username": username},
			{
				"$set": {
					"x_oauth_request_token": oauth_response.get('oauth_token'),
					"x_oauth_request_token_secret": oauth_response.get('oauth_token_secret')
				}
			}
		)
		
		# Generate authorization URL
		auth_url = oauth.authorization_url("https://api.twitter.com/oauth/authorize")
		
		return JsonResponse({
			'auth_url': auth_url,
			'oauth_token': oauth_response.get('oauth_token')
		})
		
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def x_api_oauth_callback(request):
	"""Handle X OAuth callback and complete the connection."""
	try:
		# Get OAuth parameters
		oauth_token = request.GET.get('oauth_token')
		oauth_verifier = request.GET.get('oauth_verifier')
		denied = request.GET.get('denied')
		
		if denied:
			return JsonResponse({'error': 'User denied authorization'}, status=400)
		
		if not oauth_token or not oauth_verifier:
			return JsonResponse({'error': 'Missing OAuth parameters'}, status=400)

		# Get X API credentials from environment
		x_api_key = os.environ.get('X_API_KEY')
		x_api_secret = os.environ.get('X_API_SECRET')
		
		if not x_api_key or not x_api_secret:
			return JsonResponse({'error': 'X API credentials not configured'}, status=500)

		# Find user by OAuth token
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		user = user_collection.find_one({"x_oauth_request_token": oauth_token})
		if not user:
			return JsonResponse({'error': 'Invalid OAuth token'}, status=400)
		
		username = user.get('username')
		
		# Create OAuth1 session with request token
		from requests_oauthlib import OAuth1Session
		
		oauth = OAuth1Session(
			x_api_key,
			client_secret=x_api_secret,
			resource_owner_key=oauth_token,
			resource_owner_secret=user.get('x_oauth_request_token_secret')
		)
		
		# Get access token
		access_token_url = "https://api.twitter.com/oauth/access_token"
		oauth_response = oauth.fetch_access_token(access_token_url, verifier=oauth_verifier)
		
		# Get user info using the access token
		user_oauth = OAuth1Session(
			x_api_key,
			client_secret=x_api_secret,
			resource_owner_key=oauth_response.get('oauth_token'),
			resource_owner_secret=oauth_response.get('oauth_token_secret')
		)
		
		# Get user info
		user_info_url = "https://api.twitter.com/1.1/account/verify_credentials.json"
		user_response = user_oauth.get(user_info_url)
		
		if user_response.status_code == 200:
			user_data = user_response.json()
			
			# Store the credentials
			user_collection.update_one(
				{"username": username},
				{
					"$set": {
						"x_api_credentials": {
							"access_token": oauth_response.get('oauth_token'),
							"access_token_secret": oauth_response.get('oauth_token_secret'),
							"user_id": str(user_data.get('id')),
							"username": user_data.get('screen_name'),
							"connected_at": datetime.utcnow().isoformat()
						}
					},
					"$unset": {
						"x_oauth_request_token": "",
						"x_oauth_request_token_secret": ""
					}
				}
			)
			
			# Redirect to frontend settings page with success
			from django.http import HttpResponseRedirect
			# Get the frontend URL from environment or use default
			frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
			return HttpResponseRedirect(f'{frontend_url}/settings?tab=connections&x_connected=true')
		else:
			return JsonResponse({'error': 'Failed to verify credentials'}, status=500)
		
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def x_api_disconnect(request):
	"""Disconnect user's X account."""
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

		# Remove X API credentials from user document
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		user_collection.update_one(
			{"username": username},
			{"$unset": {"x_api_credentials": ""}}
		)
		
		return JsonResponse({'success': True, 'message': 'X account disconnected successfully'})
		
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def x_api_test_connection(request):
	"""Test the X API connection for the authenticated user."""
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

		# Get user document from MongoDB
		uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
		client = MongoClient(uri)
		db = client["NeuraNet"]
		user_collection = db["users"]
		
		# Find the user by username
		user = user_collection.find_one({"username": username})
		if not user:
			return JsonResponse({'message': 'User not found'}, status=404)
		
		# Check if user has X API credentials stored
		x_credentials = user.get('x_api_credentials', {})
		
		if not x_credentials or not x_credentials.get('access_token'):
			return JsonResponse({'success': False, 'error': 'No X account connected'})
		
		# Test the connection by making a simple API call
		try:
			user_id = x_credentials.get('user_id')
			if not user_id:
				return JsonResponse({'success': False, 'error': 'No user ID stored'})
			
			x_bearer_token = os.environ.get('X_BEARER_TOKEN')
			if not x_bearer_token:
				return JsonResponse({'error': 'X API credentials not configured'}, status=500)
			
			# Test by getting user info
			url = f"https://api.twitter.com/2/users/{user_id}"
			headers = {
				'Authorization': f'Bearer {x_bearer_token}',
				'Content-Type': 'application/json'
			}
			
			response = requests.get(url, headers=headers, timeout=10)
			if response.status_code == 200:
				return JsonResponse({'success': True, 'message': 'Connection test successful'})
			else:
				return JsonResponse({'success': False, 'error': f'API call failed: {response.status_code}'})
				
		except Exception as e:
			return JsonResponse({'success': False, 'error': f'Connection test failed: {str(e)}'})
		
	except Exception as e:
		return JsonResponse({'error': f'Error: {str(e)}'}, status=500)