# Example data
devices = [
    {"device_name": "Device A", "score": 90, "sync_storage_capacity_gb": 500},
    {"device_name": "Device B", "score": 80, "sync_storage_capacity_gb": 300},
    {"device_name": "Device C", "score": 70, "sync_storage_capacity_gb": 450}
]


class AllocationService():
    def __init__(self):
        pass
    def bytes_to_gigabytes(self, bytes):
        return bytes / (1024 ** 3)  # Convert bytes to gigabytes

    def devices(self, fetched_device_predictions, file_sync_info):
        # Extract the list of devices from the nested dictionary
        devices_list = fetched_device_predictions.get("device_predictions", [])
        
        # Filter out devices with None storage capacity and set default values
        devices_list = [
            {
                **device,
                'sync_storage_capacity_gb': device.get('sync_storage_capacity_gb', 0) or 0,
                'score': device.get('score', 0) or 0
            }
            for device in devices_list
            if device.get('sync_storage_capacity_gb') is not None
        ]
        
        # Sort devices by score (descending)
        devices_list.sort(key=lambda x: x['score'], reverse=True)


        # Sort files by priority and size (descending)
        priority_map = {3: 3, 2: 2, 1: 1}
        file_sync_info = sorted(
            file_sync_info[0]['files'], 
            key=lambda x: (priority_map.get(x.get('file_priority', 1), 1), -x.get('file_size', 0)), 
            reverse=True
        )

        # Allocate files to devices
        for device in devices_list:
            device['files'] = []
            device['used_capacity'] = 0  # Initialize used capacity in gigabytes

        for file in file_sync_info:
            file_size_gb = self.bytes_to_gigabytes(file.get('file_size', 0))  # Convert file size to gigabytes
            for device in devices_list:
                if device['used_capacity'] + file_size_gb <= device['sync_storage_capacity_gb']:
                    # Store both file name and ID
                    device['files'].append({
                        'file_id': str(file['_id']),
                        'file_name': file.get('file_name', ''),
                    })
                    device['used_capacity'] += file_size_gb
                # Continue to the next device even if the file has been added

        return devices_list
    def devices_with_capacity_cap(self, fetched_device_predictions, file_sync_info, device_capacity_cap):
        # Extract the list of devices from the nested dictionary
        devices_list = fetched_device_predictions.get("device_predictions", [])
        
        # Sort devices by score (descending)
        devices_list.sort(key=lambda x: x['score'], reverse=True)

        # Sort files by priority and size (descending)
        priority_map = {3: 3, 2: 2, 1: 1}
        file_sync_info.sort(key=lambda x: (priority_map[x['file_priority']], -x['file_size']), reverse=True)

        # Allocate files to devices
        for device in devices_list:
            device['sync_storage_capacity_gb'] = device_capacity_cap
            device['files'] = []
            device['used_capacity'] = 0  # Initialize used capacity in gigabytes

        for file in file_sync_info:
            file_size_gb = self.bytes_to_gigabytes(file['file_size'])  # Convert file size to gigabytes
            for device in devices_list:
                if device['used_capacity'] + file_size_gb <= device['sync_storage_capacity_gb']:
                    # Store both file name and ID
                    device['files'].append({
                        'file_id': str(file['_id']),
                        'file_name': file['file_name'],
                    })
                    device['used_capacity'] += file_size_gb
                    break

        return devices_list

    def generate_file_device_mappings(self, allocated_devices):
        """
        Converts device-centric allocation data to file-centric mapping
        Returns a list of dictionaries, each containing a file_id and its proposed_device_ids
        """
        file_mappings = {}

        # Iterate through each device and its allocated files
        for device in allocated_devices:
            device_id = device.get('device_id')  # This is now an ObjectId
            if not device_id:
                continue

            # Go through each file allocated to this device
            for file_info in device.get('files', []):
                file_id = file_info.get('file_id')
                if not file_id:
                    continue

                # Initialize the list of device IDs if this is the first time seeing this file
                if file_id not in file_mappings:
                    file_mappings[file_id] = {
                        'file_id': file_id,
                        'proposed_device_ids': []
                    }
                
                # Add this device's ID to the file's proposed devices
                # The device_id is already an ObjectId, so we can use it directly
                file_mappings[file_id]['proposed_device_ids'].append(device_id)

        # Convert the dictionary to a list
        return list(file_mappings.values())


