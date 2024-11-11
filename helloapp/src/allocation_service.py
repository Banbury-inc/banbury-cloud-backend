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
        
        # Sort devices by score (descending)
        devices_list.sort(key=lambda x: x['score'], reverse=True)


        # Sort files by priority and size (descending)
        priority_map = {3: 3, 2: 2, 1: 1}
        file_sync_info.sort(key=lambda x: (priority_map[x['file_priority']], -x['file_size']), reverse=True)

        # Allocate files to devices
        for device in devices_list:
            device['files'] = []
            device['used_capacity'] = 0  # Initialize used capacity in gigabytes

        for file in file_sync_info:
            file_size_gb = self.bytes_to_gigabytes(file['file_size'])  # Convert file size to gigabytes
            for device in devices_list:
                if device['used_capacity'] + file_size_gb <= device['sync_storage_capacity_gb']:
                    device['files'].append(file['file_name'])
                    device['used_capacity'] += file_size_gb
                    break


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
            device['capacity'] = device_capacity_cap
            device['files'] = []
            device['used_capacity'] = 0  # Initialize used capacity in gigabytes

        for file in file_sync_info:
            file_size_gb = self.bytes_to_gigabytes(file['file_size'])  # Convert file size to gigabytes
            for device in devices_list:
                if device['used_capacity'] + file_size_gb <= device['sync_storage_capacity_gb']:
                    device['files'].append(file['file_name'])
                    device['used_capacity'] += file_size_gb
                    break

        return devices_list


