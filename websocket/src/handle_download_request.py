import json
from datetime import datetime
from apps.files.search_for_file import search_for_file

def device_group_name(device_id):
    """
    Generate a channel group name for the given device ID.
    Each device gets their own group, e.g. "device_123456".
    """
    return f"device_{device_id}"

async def handle_download_request(consumer, data):
    """Handle download request"""
    print(f"Received download request: {data}")

    username = data.get('username')
    file_name = data.get('file_name')

    response = search_for_file(username, file_name)
    
    # Get device name that has the file
    sending_device_name = response.get('device_name')
    file_path = response.get('file_path')

    # check if device is online

    # send "device is offline" message if offline


    # send the request to the device that has the file



    await consumer.channel_layer.group_send(
        device_group_name(sending_device_name),
        {
            "type": "dm_event",
            "message": "Requesting file",
            "request_type": "file_request",
            "requesting_device_name": consumer.device_name,
            "requesting_device_id": consumer.device_id,
            "file_name": file_name,
            "file_path": file_path
        }
    )