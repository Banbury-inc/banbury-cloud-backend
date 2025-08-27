import bcrypt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
import pymongo
import json
from bson import json_util
import base64
from .src.getUserFriends import getUserFriends
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def getuserinfo2(request):
    """Retrieves detailed user information (version 2)."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = request.username_from_token
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


def getfrienduserinfo(request):
    """Retrieves user information including profile picture and friends."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    
    # First check if user exists
    user = user_collection.find_one({"username": request.username_from_token})
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
        "status": "success",
        "friends": json.loads(json_util.dumps(user.get("friends", [])))  # Convert ObjectIds to strings
    }



    return JsonResponse(user_data, safe=False)



def get_small_user_info(request):
    """Retrieves basic user information (first name, last name, phone, email)."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = request.username_from_token
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



def getuserinfo3(request, password):
    """Authenticates a user based on username and password (version 3)."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": request.username_from_token})

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



@csrf_exempt
@require_http_methods(["POST"])
def update_user_profile(request):
    """Updates the user profile based on the provided data."""
    try:
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
        db = client["NeuraNet"]
        user_collection = db["users"]

        data = json.loads(request.body)


        username = data.get("username")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name") 
        phone_number = data.get("phone_number")
        email = data.get("email")
        picture = data.get("picture")

        # Find the user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({
                "result": "fail",
                "message": "User not found"
            })

        # Build update dictionary with only changed fields
        update_fields = {}
        if password and password != "undefined":
            password_bytes = password.encode("utf-8")
            update_fields["password"] = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        if first_name:
            update_fields["first_name"] = first_name
        if last_name:
            update_fields["last_name"] = last_name
        if phone_number:
            update_fields["phone_number"] = phone_number
        if email:
            update_fields["email"] = email
        if picture:
            # Check if picture size exceeds 2.5MB (2.5 * 1024 * 1024 bytes)
            picture_size = len(picture.encode('utf-8'))
            if picture_size > 2.5 * 1024 * 1024:
                return JsonResponse({
                    "result": "photo_too_large", 
                    "message": "Profile picture is too large. Maximum size is 2.5MB"
                })
            update_fields["picture"] = picture

        try:
            # Only update if there are changes
            if update_fields:
                user_collection.update_one(
                        {"username": username},
                        {"$set": update_fields}
                    )
        except:
            return JsonResponse({
                "result": "fail",
                "message": "An error occurred"
            })

        return JsonResponse({
            "result": "success",
            "message": "Profile updated successfully"
        })

    except Exception as e:
        return JsonResponse({
            "result": "fail",
            "message": f"An error occurred: {str(e)}"
        }, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def change_profile(request, password, first_name, last_name, email):
    """Updates user profile information, including optional password change."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": request.username_from_token})

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
                    "username": request.username_from_token,
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
                    "username": request.username_from_token,
                    "email": email,
                    "password": hashed_password,
                }
            },
        )

    result = "success"

    user_data = {
        "result": result,
        "username": request.username_from_token,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)

@csrf_exempt
@require_http_methods(["GET"])
def get_profile_picture(request):
    """Retrieves the profile picture for a given user."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    username = request.username_from_token
    
    user = user_collection.find_one({"username": username})
    if not user:
        return HttpResponse(status=400)  # User not found
        
    if 'picture' not in user:
        return HttpResponse(status=200)  # No picture available
        
    picture_data = user['picture']
    if not isinstance(picture_data, dict) or 'data' not in picture_data:
        return HttpResponse(status=200)  # Invalid picture data format
        
    try:
        # Try to decode the base64 data
        image_bytes = base64.b64decode(picture_data['data'])
        content_type = picture_data.get('content_type', 'image/jpeg')
        return HttpResponse(image_bytes, content_type=content_type)
    except Exception as e:
        print(f"Error decoding image for user {username}: {e}")
        return HttpResponse(status=404)  # Error decoding image

def typeahead(request, search):
    """Provides typeahead suggestions for users based on a search term."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    
    # Create text index for faster searching (run this once)
    # user_collection.create_index([
    #     ("username", "text"),
    #     ("first_name", "text"),
    #     ("last_name", "text"),
    #     ("email", "text")
    # ])
    
    # Build the query for multiple fields
    search_query = {
        "$or": [
            {"username": {"$regex": f"^{search}", "$options": "i"}},  # Starts with search term
            {"first_name": {"$regex": f"^{search}", "$options": "i"}},
            {"last_name": {"$regex": f"^{search}", "$options": "i"}},
            {"email": {"$regex": f"^{search}", "$options": "i"}}
        ]
    }
    
    # Project only needed fields and limit results
    users = user_collection.find(
        search_query,
        {
            "username": 1, 
            "first_name": 1, 
            "last_name": 1, 
            "email": 1,
            "_id": 0
        }
    ).limit(10)
    
    # Convert cursor to list
    user_list = list(users)
    
    response = {
        "result": "success",
        "users": user_list
    }
        
    return JsonResponse(response)

@csrf_exempt
@require_http_methods(["GET"])
def list_all_users(request):
    """Lists all users in the system (admin only)."""
    try:
        # Check if user is authenticated and is admin
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)
            
        # Validate token and get username
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            validated = AccessToken(token)
            username = validated.payload.get('username')
            
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
                
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)
        
        # Check if user is admin (mmills or mmills6060@gmail.com)
        if username not in ['mmills', 'mmills6060@gmail.com']:
            return JsonResponse({'message': 'Admin access required'}, status=403)
        
        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        # Build a map of file counts per user_id
        try:
            file_counts_cursor = file_collection.aggregate([
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}
            ])
            file_counts_map = {}
            system_total_files = 0
            for item in file_counts_cursor:
                key = str(item.get("_id"))
                count = int(item.get("count", 0))
                file_counts_map[key] = count
                system_total_files += count
        except Exception:
            file_counts_map = {}
            system_total_files = 0

        # Build a map of AI message counts per user_id from user collection
        try:
            ai_counts_cursor = user_collection.aggregate([
                {"$match": {"ai_message_count": {"$exists": True, "$gt": 0}}},
                {"$group": {"_id": "$_id", "count": {"$sum": "$ai_message_count"}}}
            ])
            ai_counts_map = {}
            system_total_ai_messages = 0
            for item in ai_counts_cursor:
                key = str(item.get("_id"))
                count = int(item.get("count", 0))
                ai_counts_map[key] = count
                system_total_ai_messages += count
        except Exception as e:
            print(f"Error getting AI usage stats: {e}")
            ai_counts_map = {}
            system_total_ai_messages = 0

        # Build a map of login counts and last login per user_id
        login_collection = db["user_logins"]
        try:
            # Get login counts per user
            login_counts_cursor = login_collection.aggregate([
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}, "lastLogin": {"$max": "$timestamp"}}}
            ])
            login_counts_map = {}
            last_login_map = {}
            system_total_logins = 0
            for item in login_counts_cursor:
                key = str(item.get("_id"))
                count = int(item.get("count", 0))
                last_login = item.get("lastLogin")
                login_counts_map[key] = count
                if last_login:
                    last_login_map[key] = last_login.isoformat()
                system_total_logins += count
        except Exception as e:
            print(f"Error getting login stats: {e}")
            login_counts_map = {}
            last_login_map = {}
            system_total_logins = 0

        # Get all users with basic information including Google credentials, AI usage, and subscription
        users = user_collection.find(
            {},
            {
                "_id": 1,
                "username": 1,
                "email": 1,
                "first_name": 1,
                "last_name": 1,
                "created_at": 1,
                "auth_method": 1,
                "google_drive_credentials": 1,
                "ai_message_count": 1,
                "last_ai_message_at": 1,
                "subscription": 1,
                "total_file_size": 1,
                "last_file_upload_at": 1
            }
        )
        
        # Convert cursor to list and format the data
        user_list = []
        for user in users:
            user_id_str = str(user.get("_id"))
            
            # Extract Google scopes from credentials
            google_scopes = []
            scope_count = 0
            google_credentials = user.get("google_drive_credentials", {})
            if google_credentials and "scopes" in google_credentials:
                google_scopes = google_credentials["scopes"] or []
                scope_count = len(google_scopes)
            
            # Check for individual scope types
            has_email_scope = any('userinfo.email' in scope for scope in google_scopes)
            has_profile_scope = any('userinfo.profile' in scope for scope in google_scopes)
            has_gmail_scope = any('gmail' in scope for scope in google_scopes)
            has_drive_scope = any('drive' in scope for scope in google_scopes)
            has_calendar_scope = any('calendar' in scope for scope in google_scopes)
            has_contacts_scope = any('contacts' in scope for scope in google_scopes)
            
            user_list.append({
                "_id": user_id_str,
                "username": user.get("username"),
                "email": user.get("email"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "created_at": user.get("created_at"),
                "auth_method": user.get("auth_method", "Email/Password"),
                "subscription": user.get("subscription", "free"),
                "totalFiles": file_counts_map.get(user_id_str, 0),
                "totalFileSize": user.get("total_file_size", 0),
                "lastFileUploadAt": user.get("last_file_upload_at"),
                "aiMessageCount": user.get("ai_message_count", 0),
                "lastAiMessageAt": user.get("last_ai_message_at"),
                "loginCount": login_counts_map.get(user_id_str, 0),
                "lastLoginDate": last_login_map.get(user_id_str),
                "googleScopes": google_scopes,
                "scopeCount": scope_count,
                "hasEmailScope": has_email_scope,
                "hasProfileScope": has_profile_scope,
                "hasGmailScope": has_gmail_scope,
                "hasDriveScope": has_drive_scope,
                "hasCalendarScope": has_calendar_scope,
                "hasContactsScope": has_contacts_scope
            })
        
        return JsonResponse({
            "result": "success",
            "users": user_list,
            "total_count": len(user_list),
            "system_total_files": system_total_files,
            "system_total_ai_messages": system_total_ai_messages
        })

    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ai_message_sent(request):
    """Increment AI message count for the authenticated user and return the new count."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            from rest_framework_simplejwt.tokens import AccessToken
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # DB connections
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]

        # Find user and increment AI message count atomically
        from datetime import datetime
        result = user_collection.update_one(
            {"username": username},
            {
                "$inc": {"ai_message_count": 1},
                "$set": {"last_ai_message_at": datetime.utcnow().isoformat()},
                "$setOnInsert": {"ai_usage_created_at": datetime.utcnow().isoformat()}
            }
        )

        if result.matched_count == 0:
            return JsonResponse({'message': 'User not found'}, status=404)

        # Read back the updated user document to get the latest count
        user = user_collection.find_one({"username": username})
        count = int(user.get('ai_message_count', 0)) if user else 0
        subscription = user.get('subscription', 'free') if user else 'free'

        # Check if AI message limit is exceeded (only for free users)
        if subscription == 'free' and count > 100:
            return JsonResponse({
                'result': 'exceeded_ai_message_limit',
                'message': 'AI message limit exceeded. You have reached the maximum of 100 AI messages. Please subscribe to the Pro plan for unlimited requests.',
                'username': username,
                'user_id': str(user.get('_id')),
                'aiMessageCount': count,
                'subscription': subscription
            }, status=429)  # 429 Too Many Requests

        return JsonResponse({
            'result': 'success',
            'username': username,
            'user_id': str(user.get('_id')),
            'aiMessageCount': count
        })
        
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def send_friend_request(request):
    """Sends a friend request from one user to another."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]

    data = json.loads(request.body)
    username = data.get("username")
    friend_username = data.get("friend_username")
    user = user_collection.find_one({"username": username})
    friend = user_collection.find_one({"username": friend_username})

    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})
    if not friend:
        return JsonResponse({"result": "fail", "message": "Friend not found"})

    if str(friend["_id"]) in user.get("friends", []):
        return JsonResponse({"result": "fail", "message": "Friend already added"})
    if str(friend["_id"]) in user.get("friend_requests", []):
        return JsonResponse({"result": "fail", "message": "Friend request already sent"})

    # Update the database
    user_collection.update_one(
        {"username": friend_username},
        {"$addToSet": {"friend_requests": user["_id"]}}
    )

    # Create the message payload
    message = {
        "type": "friend_request",
        "message": {
            "request_type": "friend_request",
            "from_username": username,
            "from_first_name": user.get("first_name"),
            "from_last_name": user.get("last_name")
        }
    }

    # Get the channel layer and send the message synchronously
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"user_{friend.get('_id')}", 
            message
        )
        print(f"[send_friend_request] Successfully sent websocket notification to {friend.get('username')}")
    except Exception as e:
        print(f"[send_friend_request] Error sending websocket notification: {str(e)}")
        # Continue execution even if websocket notification fails
        pass

    return JsonResponse({"result": "success", "message": "Friend request sent successfully"})


@csrf_exempt
@require_http_methods(["POST"])
def remove_friend(request):
    """Removes a friend connection between two users."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]

    data = json.loads(request.body)
    username = data.get("username")
    friend_username = data.get("friend_username")

    user = user_collection.find_one({"username": username})
    friend = user_collection.find_one({"username": friend_username})

    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})
    if not friend:
        return JsonResponse({"result": "fail", "message": "Friend not found"})
    
    user_collection.update_one(
        {"username": username},
        {"$pull": {"friends": friend["_id"]}}
    )

    user_collection.update_one(
        {"username": friend_username},
        {"$pull": {"friends": user["_id"]}}
    )

    # Create the message payload
    message = {
        "type": "friend_request",
        "message": {
            "request_type": "friend_request",
            "from_username": username,
            "from_first_name": user.get("first_name"),
            "from_last_name": user.get("last_name")
        }
    }

    # Get the channel layer and send the message synchronously
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"user_{friend.get('_id')}", 
            message
        )
        print(f"[remove_friend] Successfully sent websocket notification to {friend.get('username')}")
    except Exception as e:
        print(f"[remove_friend] Error sending websocket notification: {str(e)}")
        # Continue execution even if websocket notification fails
        pass
    return JsonResponse({"result": "success", "message": "Friend removed successfully"})


@csrf_exempt
@require_http_methods(["GET"])
def get_friends(request):
    """Retrieves the list of friends for a given user."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]

    user = user_collection.find_one({"username": request.username_from_token})
    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})

    friends = user.get("friends", [])
    friend_list = []
    for friend_id in friends:
        friend = user_collection.find_one({"_id": friend_id})
        if friend:
            friend_list.append({"username": friend.get("username"), "first_name": friend.get("first_name"), "last_name": friend.get("last_name"), "online": friend.get("online")})


    return JsonResponse({"result": "success", "friends": friend_list})


@csrf_exempt
@require_http_methods(["GET"])
def get_friend_requests(request):
    """Retrieves the list of pending friend requests for a given user."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": request.username_from_token})
    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})

    friend_requests = user.get("friend_requests", [])
    friend_requests_list = []
    for friend_id in friend_requests:
        friend = user_collection.find_one({"_id": friend_id})
        if friend:
            friend_requests_list.append({"username": friend.get("username"), "first_name": friend.get("first_name"), "last_name": friend.get("last_name")})


    return JsonResponse({"result": "success", "friend_requests": friend_requests_list})


@csrf_exempt
@require_http_methods(["POST"])
def accept_friend_request(request):
    """Accepts a pending friend request."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]

    data = json.loads(request.body)
    username = data.get("username")
    friend_username = data.get("friend_username")

    user = user_collection.find_one({"username": username})
    friend = user_collection.find_one({"username": friend_username})

    user_collection.update_one(
        {"username": username},
        {"$pull": {"friend_requests": friend["_id"]}}
    )

    user_collection.update_one(
        {"username": friend_username},
        {"$addToSet": {"friends": user["_id"]}}
    )

    user_collection.update_one(
        {"username": username},
        {"$addToSet": {"friends": friend["_id"]}}
    )

    # Create the message payload
    message = {
        "type": "friend_request",
        "message": {
            "request_type": "friend_request",
            "from_username": username,
            "from_first_name": user.get("first_name"),
            "from_last_name": user.get("last_name")
        }
    }

    # Get the channel layer and send the message synchronously
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"user_{friend.get('_id')}", 
            message
        )
        print(f"[accept_friend_request] Successfully sent websocket notification to {friend.get('username')}")
    except Exception as e:
        print(f"[accept_friend_request] Error sending websocket notification: {str(e)}")
        # Continue execution even if websocket notification fails
        pass

    return JsonResponse({"result": "success", "message": "Friend request accepted successfully"})


@csrf_exempt
@require_http_methods(["POST"])
def reject_friend_request(request):
    """Rejects a pending friend request."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]

    data = json.loads(request.body)
    username = data.get("username")
    friend_username = data.get("friend_username")

    user = user_collection.find_one({"username": username})
    friend = user_collection.find_one({"username": friend_username})

    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})
    if not friend:
        return JsonResponse({"result": "fail", "message": "Friend not found"})

    user_collection.update_one(
        {"username": username},
        {"$pull": {"friend_requests": friend["_id"]}}
    )

    user_collection.update_one(
        {"username": friend_username},
        {"$pull": {"friend_requests": user["_id"]}}
    )

    # Create the message payload
    message = {
        "type": "friend_request",
        "message": {
            "request_type": "friend_request",
            "from_username": username,
            "from_first_name": user.get("first_name"),
            "from_last_name": user.get("last_name")
        }
    }

    # Get the channel layer and send the message synchronously
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"user_{friend.get('_id')}", 
            message
        )
        print(f"[reject_friend_request] Successfully sent websocket notification to {friend.get('username')}")
    except Exception as e:
        print(f"[reject_friend_request] Error sending websocket notification: {str(e)}")
        # Continue execution even if websocket notification fails
        pass

    return JsonResponse({"result": "success", "message": "Friend request rejected successfully"})



@csrf_exempt
@require_http_methods(["GET"])
def get_user_friends(request):
    """Retrieves the list of friends for a given user using the helper function."""
    friends = getUserFriends(request.username_from_token)
    if friends: 
        return JsonResponse({"result": "success", "friends": friends})
    else:
        return JsonResponse({"result": "fail", "message": "No friends found"})



