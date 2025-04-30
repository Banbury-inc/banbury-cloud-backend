# S3 File Upload Functionality

This document provides instructions on how to set up and use the Amazon S3 file upload functionality in the Banbury Cloud backend.

## Code Structure

The S3 file upload functionality is implemented in the following files:

- `apps/files/upload_to_s3.py`: Contains the main logic for uploading files to S3
- `apps/files/views.py`: Contains a wrapper function that calls the upload function
- `apps/files/utils.py`: Contains utility functions for broadcasting new files

## Prerequisites

1. An AWS account
2. An S3 bucket created in your AWS account
3. AWS Access Key ID and Secret Access Key with permissions to upload to the S3 bucket

## Setup

### 1. Install Required Packages

Make sure you have boto3 installed:

```bash
pip install boto3
```

### 2. Configure Environment Variables

Before running the application, set the following environment variables:

```bash
export AWS_ACCESS_KEY_ID="your_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
export AWS_REGION="us-east-1"  # Replace with your preferred region
export AWS_S3_BUCKET_NAME="your-bucket-name"
```

Alternatively, use the provided script:

```bash
# Edit the script first to add your credentials
source set_s3_env.sh
```

### 3. CORS Configuration for Your S3 Bucket

If you plan to upload directly from a browser, you'll need to configure CORS on your S3 bucket. From the AWS console:

1. Navigate to your S3 bucket
2. Go to the "Permissions" tab
3. Find the "Cross-origin resource sharing (CORS)" section
4. Add a CORS configuration like this:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["*"],  // Restrict to your domain in production
    "ExposeHeaders": ["ETag"]
  }
]
```

## API Endpoint

### Upload File to S3

**URL**: `/files/upload_to_s3/<username>/`

**Method**: `POST`

**Content-Type**: `multipart/form-data`

**URL Parameters**:
- `username`: The username uploading the file

**Form Data**:
- `file`: (Required) The file to upload
- `device_name`: (Required) The name of the device from which the file is being uploaded
- `file_path`: (Optional) The file path where the file should be stored. Defaults to root.
- `file_parent`: (Optional) The parent directory of the file. Defaults to empty.

**Success Response**:
```json
{
  "result": "success",
  "file_url": "https://your-bucket-name.s3.amazonaws.com/username/timestamp_filename.ext",
  "file_info": {
    "file_name": "filename.ext",
    "file_path": "/path/to/file",
    "file_size": 12345,
    "file_type": ".ext",
    "date_uploaded": "2023-07-01T14:30:45.123456",
    "date_modified": "2023-07-01T14:30:45.123456",
    "original_device": "device_name"
  }
}
```

**Error Responses**:
- 400 Bad Request: `{"error": "No file provided."}`
- 400 Bad Request: `{"error": "Invalid file format."}`
- 400 Bad Request: `{"error": "Device name is required."}`
- 404 Not Found: `{"error": "User not found."}`
- 404 Not Found: `{"error": "Device not found."}`
- 500 Server Error: `{"error": "Failed to upload file: [error details]"}`

## Testing

1. Start the Django server
2. Open the `test_s3_upload.html` file in a browser
3. Fill in the form and upload a file
4. Check the result section for the upload status

## Client-Side Integration Example

```javascript
async function uploadFileToS3(file, username, deviceName, filePath = '', fileParent = '') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('device_name', deviceName);
  formData.append('file_path', filePath);
  formData.append('file_parent', fileParent);

  const response = await fetch(`/files/upload_to_s3/${username}/`, {
    method: 'POST',
    body: formData,
  });
  
  return await response.json();
}
``` 