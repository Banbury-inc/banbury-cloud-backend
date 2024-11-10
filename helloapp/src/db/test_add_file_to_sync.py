from datetime import datetime
import json
from .add_file_to_sync import add_file_to_sync

def test_add_file_to_sync_success():
    # Create test data with real file information
    test_data = {
        "device_name": "michael-ubuntu",
        "files": [
            {
                "file_name": "test_file.txt",
                "file_path": "/home/michael/test_file.txt",
                "file_type": "text",
                "file_size": 1024,
                "date_uploaded": datetime.now().isoformat(),
                "date_modified": datetime.now().isoformat(),
                "file_parent": "michael-ubuntu",
                "original_device": "michael-ubuntu",
                "kind": "file"
            }
        ]
    }

    # Call the function with real data
    response = add_file_to_sync(test_data, "mmills")

    # Print response for debugging
    print(response.content)

    # Add assertions
    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data["result"] == "success"
    print("Test passed successfully!")

if __name__ == "__main__":
    test_add_file_to_sync_success()