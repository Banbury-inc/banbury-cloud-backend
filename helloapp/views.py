from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import os
from bson import ObjectId
import pymongo
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from .forms import UserForm
import bcrypt
from .forms import LoginForm
from .forms import UserProfileForm
import json

def get_small_user_info(request, username):

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username 
    db = client['myDatabase']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})
    if not user:
        print("Please login first.")
    else:
        if user['username'] == username:
                first_name = user.get('first_name')
                last_name = user.get('last_name')
                phone_number = user.get('phone_number')
                email = user.get('email')
 
                user_data = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone_number": phone_number,
                        "email": email,
                        }
                return JsonResponse(user_data)



def getuserinfo2(request, username):

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username 
    db = client['myDatabase']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})
    if not user:
        print("Please login first.")
    else:
        if user['username'] == username:
                first_name = user.get('first_name')
                last_name = user.get('last_name')
                phone_number = user.get('phone_number')
                email = user.get('email')

                devices = user.get('devices', [])
                number_of_files = user.get('number_of_files', [])
                number_of_devices = user.get('number_of_devices', [])
                overall_date_added = user.get('overall_date_added', [])
                total_average_upload_speed = user.get('total_average_upload_speed', [])
                total_average_download_speed = user.get('total_average_download_speed', [])
                total_device_storage = user.get('total_device_storage', [])
 
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

def getuserinfo(request, username):

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username 
    db = client['NeuraNet']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})
    if not user:
        print("Please login first.")
    else:
        if user['username'] == username:
                first_name = user.get('first_name')
                last_name = user.get('last_name')
                phone_number = user.get('phone_number')
                email = user.get('email')
 
                user_data = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone_number": phone_number,
                        "email": email,
                        }
                return JsonResponse(user_data)
def getdeviceinfo(request, username):

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    
    if not user:
        return JsonResponse({"error": "Please login first."}, status=401)

    # Find all devices belonging to the user
    devices = list(device_collection.find({'user_id': user['_id']}))

    # Prepare devices data for response
    device_data = []
    for device in devices:
        device_data.append({
            "device_name": device.get('device_name'),
            "device_type": device.get('device_type'),
            "storage_capacity_gb": device.get('storage_capacity_gb'),
            "date_added": device.get('date_added'),
            "upload_network_speed": device.get('upload_network_speed'),
            "download_network_speed": device.get('download_network_speed'),
            "gpu_usage": device.get('gpu_usage'),
            "cpu_usage": device.get('cpu_usage'),
            "ram_usage": device.get('ram_usage'),
            "ram_total": device.get('ram_total'),
            "ram_free": device.get('ram_free'),
            "sync_status": device.get('sync_status'),
            "online": device.get('online'),
        })

    device_data = {
        "devices": device_data,
    }
    
    return JsonResponse(device_data)

def getfileinfo(request, username):

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']
    file_collection = db['files']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    
    if not user:
        return JsonResponse({"error": "Please login first."}, status=401)

    # Find all devices belonging to the user
    devices = list(device_collection.find({'user_id': user['_id']}))

    # Prepare file data for response
    all_files_data = []
    for device in devices:
        # Find all files for the current device
        files = list(file_collection.find({'device_id': device['_id']}))
        
        # Process each file and append to the list
        for file in files:
            all_files_data.append({
                "file_name": file.get('file_name'),
                "file_size": file.get('file_size'),
                "file_type": file.get('file_type'),
                "file_path": file.get('file_path'),
                "date_uploaded": file.get('date_uploaded'),
                "date_modified": file.get('date_modified'),
                "date_accessed": file.get('date_accessed'),
                "kind": file.get('kind'),
                "device_name": device.get('device_name'),  # Include device name for context
            })

    files_data = {
        "files": all_files_data,
    }
    
    return JsonResponse(files_data)
def getuserinfo3(request, username, password):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['myDatabase']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})

    if not user:
        return JsonResponse({"result": "fail", "message": "User not found. Please login first."})

    # Assuming password stored in the database is hashed and saved as bytes.
    # Also assuming 'password' parameter from the function call is the plaintext password to verify.
    stored_hashed_password = user['password']
    password_bytes = password.encode('utf-8')  # Encode the plaintext password to bytes

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get('username')
    else:
        result = "fail"
        username = None

    user_data = {
        "result": result,
        "username": username  # Return username if success, None if fail
    }
    return JsonResponse(user_data)

def getuserinfo4(request, username, password):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})

    if not user:
        return JsonResponse({"result": "fail", "message": "User not found. Please login first."})

    # Assuming password stored in the database is hashed and saved as bytes.
    # Also assuming 'password' parameter from the function call is the plaintext password to verify.
    try:
        stored_hashed_password = user['password']
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    try:
        password_bytes = password.encode('utf-8')  # Encode the plaintext password to bytes
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get('username')
    else:
        result = "fail"
        username = None

    user_data = {
        "result": result,
        "username": username  # Return username if success, None if fail
    }
    return JsonResponse(user_data)




def get_neuranet_info(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['myDatabase']
    server_data_collection = db['server']

    # Find the document
    server_data = server_data_collection.find_one({})

    # Extract the specific fields
    total_data_processed = server_data.get('total_data_processed', None)
    total_number_of_requests = server_data.get('total_number_of_requests', None)

    collected_server_data = {
        "total_data_processed": total_data_processed,
        "total_number_of_requests": total_number_of_requests
    }

    return JsonResponse(collected_server_data)




@csrf_exempt
def update_devices(request, username):
    if request.method == 'POST':
        try:
            # Load JSON data from the request body
            data = json.loads(request.body)
            new_files = data.get('files', [])
            device_name = data.get('device_name')

            # Connection URI to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client['myDatabase']
            user_collection = db['users']

            # Find the user by username
            user = user_collection.find_one({'username': username})

            # Update the files array for the specific device
            result = user_collection.update_one(
                {'_id': user['_id'], 'devices.device_name': device_name},
                {'$set': {'devices.$.files': new_files}}
            )

            # Check if the update was successful
            if result.modified_count > 0:
                return JsonResponse({'response': 'success'})
            else:
                # return JsonResponse({'error': 'Device not found or no update needed'}, status=404)
                return JsonResponse({'response': 'no change needed'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'GET':
        return JsonResponse({'response': 'success'})

    else:
        return JsonResponse({'error': 'Invalid method'}, status=405)



def change_profile(request, username, password, first_name, last_name, email):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['myDatabase']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})

    if not user:
        return JsonResponse({"result": "fail", "message": "User not found. Please login first."})

    if password == "undefined":

       user_collection.update_one({'_id': user['_id']}, {'$set': {
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'email': email,
            }})
    else:
        password_bytes = password.encode('utf-8')  # Encode the string to bytes
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
 
        user_collection.update_one({'_id': user['_id']}, {'$set': {
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'email': email,
            'password': hashed_password,
            }})
 
    result = "success"

    user_data = {
        "result": result,
        "username": username  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


def register(request, username, password, firstName, lastName):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['myDatabase']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})

    password_bytes = password.encode('utf-8')  # Encode the string to bytes
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    if user:
        user_data = {
            "result": "user_already_exists",
            "username": username
        }
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
        "username": username  # Return username if success, None if fail
    }
    return JsonResponse(user_data)
 
def new_register(request, username, password, firstName, lastName):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    user = user_collection.find_one({'username': username})

    password_bytes = password.encode('utf-8')  # Encode the string to bytes
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    if user:
        user_data = {
            "result": "user_already_exists",
            "username": username
        }
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
        "username": username  # Return username if success, None if fail
    }
    return JsonResponse(user_data)

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_device(request, username, device_name):
    try:
        data = json.loads(request.body)
        device_name = data.get('device_name')
        device_type = data.get('device_type')
        storage_capacity_gb = data.get('storage_capacity_gb')
        date_added = data.get('date_added')
        upload_network_speed = data.get('upload_network_speed')
        download_network_speed = data.get('download_network_speed')
        gpu_usage = data.get('gpu_usage')
        cpu_usage = data.get('cpu_usage')
        ram_usage = data.get('ram_usage')
        ram_total = data.get('ram_total')
        ram_free = data.get('ram_free')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    device_collection = db['devices']
    user_collection = db['users']

    # Find the user_id based on username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"result": "error", "message": "Device not found."})

    user_id = user['_id']  # Get the ObjectId for the device

    new_device = {
            "user_id": user_id,
            "device_name": device_name,
            "device_type": device_type,
            "storage_capacity_gb": storage_capacity_gb,
            "date_added": [],
            "upload_network_speed": [],
            "download_network_speed": [],
            "gpu_usage": [],
            "cpu_usage": [],
            "ram_usage": [],
            "ram_total": [],
            "ram_free": [],
            "sync_status": False,
            "online": True
    }

    try:
        # Insert the new device and get the inserted_id
        result = device_collection.insert_one(new_device)
        device_id = result.inserted_id

        # Update the user collection to add the device_id to the user's list of devices
        user_collection.update_one(
            {"_id": user_id},
            {"$push": {"devices": device_id}}
        )

        # Append all usage data and other arrays in the device document
        device_collection.update_one(
            {"_id": device_id},
            {
                "$push": {
                    "gpu_usage": gpu_usage,
                    "cpu_usage": cpu_usage,
                    "ram_usage": ram_usage,
                    "ram_total": ram_total,
                    "ram_free": ram_free,
                    "download_network_speed": download_network_speed,
                    "upload_network_speed": upload_network_speed,
                    "date_added": date_added
                }
            }
        )

    except Exception as e:
        print(f"Error sending to device: {e}")

    result = "success"

    user_data = {
        "result": result,
        "username": username  # Return username if success, None if fail
    }
    return JsonResponse(user_data)
 


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_file(request, username):

        try:
            # Parse the JSON body
            data = json.loads(request.body)
            
            # Extract specific data from the JSON (for example: device_id and date_added)
            file_type = data.get('file_type')
            file_name = data.get('file_name')
            file_path = data.get('file_path')
            date_uploaded = data.get('date_uploaded')
            date_modified = data.get('date_modified')
            file_size = data.get('file_size')
            file_priority = data.get('file_priority')
            file_parent = data.get('file_parent')
            original_device = data.get('original_device')
            kind = data.get('kind')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)


        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        file_collection = db['files']
        device_collection = db['devices']

        # Find the device_id based on device_name
        device = device_collection.find_one({"device_name": original_device})
        if not device:
            return JsonResponse({"result": "device_not_found", "message": "Device not found."})

        try:
            device_id = device['_id']  # Get the ObjectId for the device
        except:
            return JsonResponse({"result": "object_id_not_found", "message": "Device id not found."})

        new_file = {
                "device_id": device_id,
                "file_type": file_type,
                "file_name": file_name,
                "file_path": file_path,
                "date_uploaded": date_uploaded,
                "date_modified": date_modified,
                "file_size": file_size,
                "file_priority": file_priority,
                "file_parent": file_parent,
                "original_device": original_device,
                "kind": kind
       }

        try:
            file_collection.insert_one(new_file)
        except Exception as e:
            print(f"Error sending to device: {e}")
        result = "success"

        user_data = {
            "result": result,
            "username": username  # Return username if success, None if fail
        }
        return JsonResponse(user_data)

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_task(request, username):

        try:
            # Parse the JSON body
            data = json.loads(request.body)
            # Extract specific data from the JSON (for example: device_id and date_added)
            task_name = data.get('task_name')
            task_device = data.get('task_device')
            task_status = data.get('task_status')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)


        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        session_collection = db['sessions']
        device_collection = db['devices']

        # Find the device_id based on device_name
        device = device_collection.find_one({"device_name": task_device})
        if not device:
            return JsonResponse({"result": "device_not_found", "message": "Device not found."})

        try:
            device_id = device['_id']  # Get the ObjectId for the device
        except:
            return JsonResponse({"result": "object_id_not_found", "message": "Device id not found."})

        new_task = {
                "device_id": device_id,
                "username": username,
                "task_name": task_name,
                "task_device": task_device,
                "task_status": task_status,
       }

        try:
            session_collection.insert_one(new_task)
        except Exception as e:
            print(f"Error sending to device: {e}")
        result = "success"

        user_data = {
            "result": result,
            "username": username  # Return username if success, None if fail
        }
        return JsonResponse(user_data)

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def update_task(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        task_name = data.get('task_name')
        task_device = data.get('task_device')  # You may also want to use the device name for better specificity
        task_status = data.get('task_status')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not task_name or not task_status:
        return JsonResponse({'error': 'Missing task_name or task_status'}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    session_collection = db['sessions']

    # Use both task_name and task_device to find the specific task
    query = {"task_name": task_name}
    if task_device:
        query["task_device"] = task_device

    # Update the task with the new status
    update_result = session_collection.update_one(
        query,
        {"$set": {"task_status": task_status}}
    )

    if update_result.matched_count == 0:
        return JsonResponse({"result": "task_not_found", "message": "Task not found."})

    return JsonResponse({"result": "success", "message": "Task status updated successfully."})    

@csrf_exempt
@require_http_methods(["POST"])
def get_session(request, username):
        # Parse the JSON body
        data = json.loads(request.body)
        task_device = data.get('task_device')
        
        if not task_device:
            return JsonResponse({"result": "no_device_provided", "message": "No device provided."}, status=400)
        if not username:
            return JsonResponse({"result": "no_username_provided", "message": "No username provided."}, status=400)
        

        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        try:
            session_collection = db['sessions']
        except:
            return JsonResponse({"error": "Can't find session collection"})

        sessions = session_collection.find({"username": username, "task_device": task_device})

        # Convert the cursor to a list of dictionaries and serialize ObjectId to string
        session_list = []
        for session in sessions:
            session['_id'] = str(session['_id'])  # Convert ObjectId to string
            session['device_id'] = str(session['device_id'])  # Convert device_id ObjectId to string
            session_list.append(session)

            # Use json.dumps to serialize the data, ensuring all elements are JSON-compatible
        response_data = {
            "result": "success",
            "sessions": session_list
        }

        return JsonResponse(response_data, status=200)

    

# def registration_api(request, firstName, lastName, username, password):

#  
#     uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"

#     client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
#     db = client['myDatabase']
#     user_collection = db['users']

#     # Ensure the request body is JSON

#     hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

#     # Create a new user document with additional fields set to null
#     new_user = {
#         "username": username,
#         "password": hashed_password,
#         "first_name": firstName,
#         "last_name": lastName,
#         "phone_number": None,
#         "email": None,
#         "devices": [],
#         "number_of_devices": [],
#         "number_of_files": [],
#         "overall_date_added": [],
#         "total_average_download_speed": [],
#         "total_average_upload_speed": [],
#         "total_device_storage": [],
#         "total_average_cpu_usage": [],
#         "total_average_gpu_usage": [],
#         "total_average_ram_usage": [],
#     }


#     try:
#         user_collection.insert_one(new_user)
#         message = {
#             "response": "success",
#                 } 
#         return JsonResponse(message)
#     except Exception as e:
#         message = {
#             "response": "fail",
#         }
#         return JsonResponse(message)


def homepage(request):
    service = os.environ.get('K_SERVICE', 'Unknown service')
    revision = os.environ.get('K_REVISION', 'Unknown revision')
    
    return render(request, 'homepage.html', context={
        "message": "It's running!",
        "Service": service,
        "Revision": revision,
    })

def aboutpage(request):
    return render(request, 'aboutpage.html', context={})


def download_debian_package(request):
    file_path = os.path.join(settings.BASE_DIR, 'helloapp/templates/bcloud_1.0.0_all.deb')
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.debian.binary-package")
            response['Content-Disposition'] = 'attachment; filename="bcloud_1.0.0.0_all.deb"'
            return response
    else:
        response = HttpResponse("File not found.", status=404)
    return response


def addusernopassword(request):
    # MongoDB connection string

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    # Create a MongoDB client
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))

    # Select the database and collection
    db = client['myDatabase']
    user_collection = db['users']

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            # Insert the user into the database
            try:
                user_collection.insert_one({"username": username})
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"
            return render(request, 'user_added.html', {'message': message})
    else:
        form = UserForm()

    return render(request, 'add_user.html', {'form': form})
def adduser1(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
    db = client['myDatabase']
    user_collection = db['users']

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['first_name']
            username = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']  # Get the password from the form

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            try:
                # Insert the user with the hashed password into the database
                user_collection.insert_one({"username": username, "password": hashed_password})
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"
            return render(request, 'user_added.html', {'message': message})
    else:
        form = UserForm()

    return render(request, 'add_user.html', {'form': form})

def adduser(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
    db = client['myDatabase']
    user_collection = db['users']


    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            firstName = form.cleaned_data['first_name']
            lastName = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password'].encode('utf-8')

            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

            # Create a new user document with additional fields set to null
            new_user = {
                "username": username,
                "password": hashed_password,
                "first_name": firstName,
                "last_name": lastName,
                "phone_number": None,
                "email": None,
                "devices": [],
                "files": []
            }

            try:
                user_collection.insert_one(new_user)
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"

            return render(request, 'user_added.html', {'message': message})

    else:
        form = UserForm()

    return render(request, 'add_user.html', {'form': form})


def login(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
    db = client['myDatabase']
    user_collection = db['users']

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password'].encode('utf-8')

            user = user_collection.find_one({'username': username})

            if user and bcrypt.checkpw(password, user['password']):
                return redirect('dashboard', username=username)  # Redirect to a home page or dashboard
            else:
                return render(request, 'login.html', {'form': form, 'error': 'Invalid username or password'})
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def login_api(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
    db = client['myDatabase']
    user_collection = db['users']

    # Ensure the request body is JSON
    try:
        data = json.loads(request.body)

        # extract username and password from the JSON data
        username = data.get('username')
        password = data.get('password').encode('utf-8')

        user = user_collection.find_one({'username': username})

        if user and bcrypt.checkpw(password, user['password']):
            return JsonResponse({'response': 'success'})
        else:
            return JsonResponse({'response': 'fail'})


    except ValueError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)




def dashboard(request, username):
    # Render the dashboard template with the username
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
    db = client['myDatabase']
    user_collection = db['users']

    user = user_collection.find_one({'username': username})
    first_name = user.get('first_name', 'User')  # Default to 'User' if first name is not set
    files = user.get('files', 'files')  # Default to 'User' if first name is not set
    devices = user.get('devices', 'devices')  # Default to 'User' if first name is not set
    return render(request, 'dashboard.html', {'username': username, 'first_name': first_name, 'files': files, 'devices': devices})

def update_user_profile(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
    db = client['myDatabase']
    user_collection = db['users']




    user = user_collection.find_one({'username': username})

    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user_collection.update_one(
                {'username': username},
                {'$set': {
                    'first_name': form.cleaned_data['first_name'] or user['first_name'],
                    'last_name': form.cleaned_data['last_name'] or user['last_name'],
                    'phone_number': form.cleaned_data['phone_number'] or user['phone_number'],
                    'email': form.cleaned_data['email'] or user['email']
                }}
            )
            return redirect('dashboard', username=username)
    else:
        form = UserProfileForm(initial=user)

    return render(request, 'update_profile.html', {'form': form, 'username': username})



