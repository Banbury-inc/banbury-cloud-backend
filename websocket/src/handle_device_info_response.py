import json

async def handle_device_info_response(consumer,data):
    """Handle device info response"""
    print(f"Received device info response: {data}")

    await consumer.send(text_data=json.dumps({
        'message': "Device info received",
        'device_info': data.get('device_info'),
    }))
