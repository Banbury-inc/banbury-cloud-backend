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

    # Store transfer room information in consumer
    if transfer_room:
        consumer.transfer_room = transfer_room
        
        # Initialize active_transfer_rooms if needed
        if not hasattr(consumer, 'active_transfer_rooms'):
            consumer.active_transfer_rooms = set()
        consumer.active_transfer_rooms.add(transfer_room)
        
        # Store in scope as well for redundancy
        consumer.scope['transfer_room'] = transfer_room
        if not consumer.scope.get('transfer_rooms'):
            consumer.scope['transfer_rooms'] = set()
        consumer.scope['transfer_rooms'].add(transfer_room)
        
        print(f"Stored transfer room {transfer_room} in consumer attributes for file transfer")

    # Add sending device to transfer room
    await consumer.channel_layer.group_add(
        transfer_room,
        consumer.channel_name
    )
    print(f"Added sending device to transfer room: {transfer_room}")

    # Send confirmation back to client
    await consumer.send(text_data=json.dumps({
        "type": "file_transfer_started",
        "file_name": file_name,
        "file_path": file_path,
        "transfer_room": transfer_room
    }))