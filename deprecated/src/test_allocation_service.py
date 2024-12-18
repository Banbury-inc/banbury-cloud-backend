import unittest
from allocation_service import AllocationService

# Sample data for testing
devices = [
    {"device_name": "Device A", "score": 90, "capacity": 500},
    {"device_name": "Device B", "score": 80, "capacity": 300},
    {"device_name": "Device C", "score": 70, "capacity": 450}
]

files = [
    {"file_name": "File 1", "size": 300 * (1024 ** 3), "priority": "high"},
    {"file_name": "File 2", "size": 100 * (1024 ** 3), "priority": "medium"},
    {"file_name": "File 3", "size": 200 * (1024 ** 3), "priority": "low"},
    {"file_name": "File 4", "size": 150 * (1024 ** 3), "priority": "high"},
]

class TestAllocationService(unittest.TestCase):
    def setUp(self):
        self.service = AllocationService()

    def test_bytes_to_gigabytes(self):
        # Test conversion function
        bytes_size = 1024 ** 3  # 1 GB in bytes
        result = self.service.bytes_to_gigabytes(bytes_size)
        self.assertEqual(result, 1)

    def test_devices_allocation(self):
        # Test file allocation with varying device capacities
        allocated_devices = self.service.devices(devices.copy(), files.copy())

        # Check allocation results for each device
        self.assertEqual(len(allocated_devices[0]['files']), 2)  # Device A gets two files
        self.assertEqual(len(allocated_devices[1]['files']), 2)  # Device B gets two files
        self.assertEqual(len(allocated_devices[2]['files']), 0)  # Device C gets no files

        # Check used capacity
        self.assertLessEqual(allocated_devices[0]['used_capacity'], allocated_devices[0]['capacity'])
        self.assertLessEqual(allocated_devices[1]['used_capacity'], allocated_devices[1]['capacity'])
        self.assertLessEqual(allocated_devices[2]['used_capacity'], allocated_devices[2]['capacity'])

    def test_devices_with_capacity_cap(self):
        # Test file allocation with a capacity cap of 200 GB for each device
        device_cap = 200
        allocated_devices = self.service.devices_with_capacity_cap(devices.copy(), files.copy(), device_cap)

        # Ensure each device respects the capacity cap
        for device in allocated_devices:
            self.assertEqual(device['capacity'], device_cap)
            self.assertLessEqual(device['used_capacity'], device_cap)

        # Check that files are allocated based on priority within the new capacity limits
        self.assertEqual(len(allocated_devices[0]['files']), 1)  # Device A gets one file
        self.assertEqual(len(allocated_devices[1]['files']), 1)  # Device B gets one file
        self.assertEqual(len(allocated_devices[2]['files']), 1)  # Device C gets one file

if __name__ == "__main__":
    unittest.main()

