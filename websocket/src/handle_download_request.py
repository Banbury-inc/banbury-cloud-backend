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
    """Handle download request between devices"""
    file_name = data.get("file_name")
    file_info = data.get("file_info")
    sending_device_id = file_info[0].get("device_id") if file_info else None
    file_path = file_info[0].get("file_path") if file_info else None
    requesting_device_id = data.get("requesting_device_id")  # Get from request data instead of consumer
    
    print(f"Setting up transfer between sender {sending_device_id} and requester {requesting_device_id}")

    if not all([file_name, sending_device_id, requesting_device_id]):
        await consumer.send(text_data=json.dumps({
            "type": "error",
            "message": "Missing required information for download"
        }))
        return

    try:
        # Create a unique transfer room name
        transfer_room = f"transfer_{sending_device_id}_{requesting_device_id}"
        print(f"Creating transfer room: {transfer_room}")
        
        # Add requesting device to transfer room
        await consumer.channel_layer.group_add(
            transfer_room,
            consumer.channel_name
        )
        print(f"Added requesting device to transfer room: {transfer_room}")

        # Send to the device that has the file
        await consumer.channel_layer.group_send(
            f"device_{sending_device_id}",
            {
                "type": "file_request_event",
                "message": "file_request",
                "file_name": file_name,
                "file_path": file_path,
                "requesting_device_id": requesting_device_id,
                "transfer_room": transfer_room,
                "timestamp": datetime.now().isoformat()
            }
        )
        print(f"Sent file request to sending device: {sending_device_id}")

        # Send confirmation to requesting device
        await consumer.send(text_data=json.dumps({
            "type": "download_request_sent",
            "file_name": file_name,
            "sending_device_id": sending_device_id,
            "transfer_room": transfer_room,  # Include transfer room in response
            "timestamp": datetime.now().isoformat()
        }))

    except Exception as e:
        print(f"Error in download request: {str(e)}")
        await consumer.send(text_data=json.dumps({
            "type": "error",
            "message": f"Failed to send download request: {str(e)}"
        }))