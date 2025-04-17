"""
Configuration file to control TensorFlow logging.
This file can be imported at application startup to silence TensorFlow warnings.
"""
import os
import logging

# Set TensorFlow log level to suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR

# Suppress other TensorFlow-related logs
logging.getLogger('tensorflow').setLevel(logging.ERROR) 