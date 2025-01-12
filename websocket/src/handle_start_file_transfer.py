import json
from datetime import datetime

def device_group_name(device_id):
    """
    Generate a channel group name for the given device ID.
    Each device gets their own group, e.g. "device_123456".
    """
    return f"device_{device_id}"

async def handle_start_file_transfer(consumer, data):
    """Handle start file transfer"""
    print(f"Received start file transfer: {data}")
    file_name = data.get("file_name")
    file_path = data.get("file_path")
    transfer_room = data.get("transfer_room")
    requesting_device_id = data.get("requesting_device_id")
    sending_device_id = consumer.device_id

    print(f"Setting up transfer between sender {sending_device_id} and requester {requesting_device_id}")

    # Add requesting device to transfer room
    await consumer.channel_layer.group_add(
        transfer_room,
        consumer.channel_name
    )
    print(f"Added requesting device to transfer room: {transfer_room}")

    # Send confirmation back to client
    await consumer.send(text_data=json.dumps({
        "type": "file_transfer_started",
        "file_name": file_name,
        "file_path": file_path,
        "transfer_room": transfer_room
    }))