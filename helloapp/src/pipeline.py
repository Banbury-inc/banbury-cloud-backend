# pipeline for prediction service

from .db import get_device_info

device_info = get_device_info("mmills")

print(device_info)
