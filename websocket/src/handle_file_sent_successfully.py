import json
from datetime import datetime
from apps.predictions.pipeline import pipeline

async def handle_file_sent_successfully(data):
    """Handle file sent successfully"""
    print(f"Received file sent successfully: {data}")
