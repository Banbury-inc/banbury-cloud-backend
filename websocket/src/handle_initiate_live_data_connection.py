import json
from datetime import datetime
from apps.predictions.pipeline import pipeline
import asyncio
from ..src.make_device_predictions import make_device_predictions as external_make_device_predictions

async def handle_initiate_live_data_connection(consumer, data):
    """Handle initiate live data connection"""
    print(f"Received initiate live data connection: {data}")
    run_device_info_loop = data.get("run_device_info_loop")
    run_device_predictions_loop = data.get("run_device_predictions_loop")
    username = data.get("username")
    device_name = data.get("device_name")

    # Create tasks for both loops
    tasks = []
    if run_device_info_loop:
        tasks.append(request_device_info(consumer, device_name))
    if run_device_predictions_loop:
        tasks.append(make_device_predictions(consumer, username, device_name))

    # Run both tasks concurrently if they exist
    if tasks:
        await asyncio.gather(*tasks)

async def make_device_predictions(consumer, username, device_name):
    """Run predictions loop"""
    while True:  # Continuous loop
        try:
            result = await external_make_device_predictions(username, device_name)
            data = result.get("data")
            print(data)
            print(f"Sending predictions request to {device_name}")
            await consumer.send(text_data=json.dumps({
                'message': "File sync request",
                'download_queue': result,
                'request_type': 'file_sync_request',
            }))
            await asyncio.sleep(1800)  # 30 minutes
        except Exception as e:
            print(f"Error in predictions loop: {str(e)}")
            break

async def request_device_info(consumer, device_name):
    """Run device info request loop"""
    while True:  # Continuous loop
        try:
            print(f"Requesting device information from {device_name}")
            await consumer.send(text_data=json.dumps({
                'message': "Requesting device information",
                'request_type': 'device_info'
            }))
            await asyncio.sleep(1800)  # 30 minutes
        except Exception as e:
            print(f"Error in device info loop: {str(e)}")
            break