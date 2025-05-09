"""
API Key management configuration file.
This file stores the valid API keys for the application.
"""
import os
from django.core.exceptions import ImproperlyConfigured

# Load API keys from environment variables for security
# Format should be a comma-separated list of keys
API_KEYS_ENV = os.environ.get('BANBURY_API_KEYS', '')
if not API_KEYS_ENV:
    # For development only - remove in production
    # In production, API keys should always come from secure environment variables
    API_KEYS = ['dev_key_1', 'dev_key_2']
else:
    API_KEYS = [key.strip() for key in API_KEYS_ENV.split(',')]

# Validate that we have at least one API key
if not API_KEYS:
    raise ImproperlyConfigured(
        "No API keys configured. Please set the BANBURY_API_KEYS environment variable."
    ) 