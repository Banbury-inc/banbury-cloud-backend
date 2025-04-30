#!/bin/bash

# Set S3 configuration environment variables
export AWS_ACCESS_KEY_ID="your_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
export AWS_REGION="us-east-1"  # Change to your preferred region
export AWS_S3_BUCKET_NAME="your-bucket-name"

echo "S3 environment variables set successfully."
echo "Run the script with: source set_s3_env.sh" 