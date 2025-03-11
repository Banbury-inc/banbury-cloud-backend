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
from .src.getUserFriends import getUserFriends
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
        "status": "success",
        "friends": json.loads(json_util.dumps(user.get("friends", [])))  # Convert ObjectIds to strings
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



@api_view(["POST"])
def update_user_profile(request):
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
    if not user:
        return HttpResponse(status=400)  # User not found
        
    if 'picture' not in user:
        return HttpResponse(status=400)  # No picture available
        
    picture_data = user['picture']
    if not isinstance(picture_data, dict) or 'data' not in picture_data:
        return HttpResponse(status=400)  # Invalid picture data format
        
    try:
        # Try to decode the base64 data
        image_bytes = base64.b64decode(picture_data['data'])
        content_type = picture_data.get('content_type', 'image/jpeg')
        return HttpResponse(image_bytes, content_type=content_type)
    except Exception as e:
        print(f"Error decoding image for user {username}: {e}")
        return HttpResponse(status=404)  # Error decoding image

@api_view(["GET"])
def typeahead(request, search):
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

@api_view(["POST"])
def send_friend_request(request):
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


@api_view(["POST"])
def remove_friend(request):
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


@api_view(["GET"])
def get_friends(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]

    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})

    friends = user.get("friends", [])
    friend_list = []
    for friend_id in friends:
        friend = user_collection.find_one({"_id": friend_id})
        if friend:
            friend_list.append({"username": friend.get("username"), "first_name": friend.get("first_name"), "last_name": friend.get("last_name"), "online": friend.get("online")})


    return JsonResponse({"result": "success", "friends": friend_list})


@api_view(["GET"])
def get_friend_requests(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"result": "fail", "message": "User not found"})

    friend_requests = user.get("friend_requests", [])
    friend_requests_list = []
    for friend_id in friend_requests:
        friend = user_collection.find_one({"_id": friend_id})
        if friend:
            friend_requests_list.append({"username": friend.get("username"), "first_name": friend.get("first_name"), "last_name": friend.get("last_name")})


    return JsonResponse({"result": "success", "friend_requests": friend_requests_list})


@api_view(["POST"])
def accept_friend_request(request):
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


@api_view(["POST"])
def reject_friend_request(request):
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



@api_view(["GET"])
def get_user_friends(request, username):
    friends = getUserFriends(username)
    if friends: 
        return JsonResponse({"result": "success", "friends": friends})
    else:
        return JsonResponse({"result": "fail", "message": "No friends found"})



