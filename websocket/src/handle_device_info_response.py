import json
from datetime import datetime
from apps.predictions.pipeline import pipeline

async def handle_device_info_response(data):
    """Handle device info response"""
    print(f"Received device info response: {data}")
