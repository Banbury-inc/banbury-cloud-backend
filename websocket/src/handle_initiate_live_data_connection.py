import json
from datetime import datetime
from apps.predictions.pipeline import pipeline

async def handle_initiate_live_data_connection(data):
    """Handle initiate live data connection"""
    print(f"Received initiate live data connection: {data}")
