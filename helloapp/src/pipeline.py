# pipeline for prediction service

import scoring_service
import prediction_service
import allocation_service
from db import get_device_info
from db import get_files_info

device_info = get_device_info("mmills6060")
print(device_info)

files_info = get_files_info("mmills6060")
print(files_info)