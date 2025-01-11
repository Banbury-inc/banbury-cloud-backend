import json
from datetime import datetime
from apps.predictions.pipeline import pipeline

async def handle_file_transfer_complete(data):
    """Handle file transfer complete"""
    print(f"Received file transfer complete: {data}")
