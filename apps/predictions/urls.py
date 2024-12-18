from django.urls import path
from . import views

urlpatterns = [
    path("run_pipeline/<str:username>/", views.run_pipeline, name="run_pipeline"),
    path("add_file_to_sync/<str:username>/", views.add_file_to_sync, name="add_file_to_sync"),
    path("get_files_to_sync/<str:username>/", views.get_files_to_sync, name="get_files_to_sync"),
    path("update_file_priority/<str:username>/", views.update_file_priority, name="update_file_priority"),
    path("update_sync_storage_capacity/<str:username>/", views.update_sync_storage_capacity, name="update_sync_storage_capacity"),
    path("get_download_queue/<str:username>/", views.get_download_queue, name="get_download_queue"),
    path("get_device_prediction_data/<str:username>/", views.get_device_prediction_data, name="get_device_prediction_data"),
]
