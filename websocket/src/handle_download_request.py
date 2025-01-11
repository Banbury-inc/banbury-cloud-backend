import json
from datetime import datetime
from apps.predictions.pipeline import pipeline

async def handle_download_request(data):
    """Handle download request"""
    print(f"Received download request: {data}")
