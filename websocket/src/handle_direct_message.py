import json
from datetime import datetime
from apps.predictions.pipeline import pipeline

def device_group_name(device_id):
    """
    Generate a channel group name for the given device ID.
    Each device gets their own group, e.g. "device_123456".
    """
    return f"device_{device_id}"


async def handle_direct_message(consumer, data):
    """Handle direct message"""
    print(f"Received direct message: {data}")

    to_device_id = data.get("to_device_id")
    message = data.get("message", "")
    from_device_id = consumer.device_id

    print(f"to_device_id: {to_device_id}, message: {message}, from_device_id: {from_device_id}")

    await consumer.channel_layer.group_send(
        device_group_name(to_device_id),
        {
            "type": "dm_event",
            "message": message,
            "sender_id": from_device_id
        }
    )
