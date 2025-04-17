from datetime import datetime
from apps.predictions.pipeline import pipeline

async def make_device_predictions(username, device_name):
    """Call pipeline"""
    print(f"Making device predictions for {username}")
    result = await pipeline(username)

    def convert_datetime(obj):
        """Recursively convert datetime objects to ISO format strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: convert_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_datetime(item) for item in list(obj)]
        return obj

    # Convert all datetime objects in the result
    result = convert_datetime(result)

    return result
