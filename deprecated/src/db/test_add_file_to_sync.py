from datetime import datetime
import json
from .add_file_to_sync import add_file_to_sync

def test_add_file_to_sync_success():


    test_data = [
        {"file_name": "test_file.txt", "file_path": "/home/michael/test_file.txt", "file_type": "text", "file_size": 1024, "date_uploaded": datetime.now().isoformat(), "date_modified": datetime.now().isoformat(), "file_parent": "michael-ubuntu", "original_device": "michael-ubuntu", "kind": "file"}
    ]
    result = add_file_to_sync("mmills", "michael-ubuntu", test_data)
    print(result)

if __name__ == "__main__":
    test_add_file_to_sync_success()