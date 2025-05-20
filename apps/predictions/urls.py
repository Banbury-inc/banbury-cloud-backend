from django.urls import path
from . import views

urlpatterns = [
    path("run_pipeline/", views.run_pipeline, name="run_pipeline"),
    path("add_file_to_sync/", views.add_file_to_sync, name="add_file_to_sync"),
    path("get_files_to_sync/", views.get_files_to_sync, name="get_files_to_sync"),
    path("update_file_priority/", views.update_file_priority, name="update_file_priority"),
    path("update_sync_storage_capacity/", views.update_sync_storage_capacity, name="update_sync_storage_capacity"),
    path("get_download_queue/", views.get_download_queue, name="get_download_queue"),
    path("get_device_prediction_data/", views.get_device_prediction_data, name="get_device_prediction_data"),
    path("add_device_id_to_file_sync_file/", views.add_device_id_to_file_sync_file, name="get_device_prediction_data"),
    path("remove_file_from_sync/", views.remove_file_from_sync, name="remove_file_from_sync"),
]
