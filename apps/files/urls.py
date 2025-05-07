from django.urls import path
from . import views

urlpatterns = [
    path("add_file/", views.add_file, name="add_file"),
    path("add_files/", views.add_files, name="add_files"),
    path("add_scanned_folder/", views.add_scanned_folder, name="add_scanned_folder"),
    path("delete_files/", views.handle_delete_files, name="add_files"),
    path("update_files/", views.handle_update_files, name="add_files"),
    path("getfileinfo/", views.getfileinfo, name="getfileinfo"),
    path("get_files_from_filepath/", views.get_files_from_filepath, name="get_file_info_from_filepath"),
    path("paginated_get_files_info/", views.paginated_get_files_info, name="paginated_get_files_info"),
    path("getpartialfileinfo/",views.get_partial_file_info,name="getpartialfileinfo",),
    path("search_file/", views.search_file, name="search_file"),
    path("get_scanned_folders/", views.get_scanned_folders, name="get_scanned_folders"),
    path("remove_scanned_folder/", views.remove_scanned_folder, name="remove_scanned_folder"),
    path("share_file/", views.share_file, name="share_file"),
    path("make_file_public/", views.make_file_public, name="make_file_public"),
    path("make_file_private/", views.make_file_private, name="make_file_private"),
    path("get_shared_files/", views.get_shared_files, name="get_shared_files"),
    path("get_shared_files_from_filepath/", views.get_shared_files_from_filepath, name="get_shared_files_from_filepath"),
    path("get_file_info/<str:file_id>/", views.get_file_info, name="get_file_info"),
    path("upload_to_s3/", views.upload_to_s3, name="upload_to_s3"),
    path("get_s3_files/", views.get_s3_files, name="get_s3_files"),
    path("download_s3_file/<str:file_id>/", views.download_s3_file_view, name="download_s3_file"),
]
