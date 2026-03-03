import base64
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bson import ObjectId


def serialize_value(value: Any):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("utf-8")
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    return str(value)
