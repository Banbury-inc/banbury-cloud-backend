from django.urls import path
from . import views

urlpatterns = [
    path("add_file/<str:username>/", views.add_file, name="add_file"),
    path("add_files/<str:username>/", views.add_files, name="add_files"),
    path("delete_files/<str:username>/", views.handle_delete_files, name="add_files"),
    path("update_files/<str:username>/", views.handle_update_files, name="add_files"),
    path("getfileinfo/<str:username>/", views.getfileinfo, name="getfileinfo"),
    path("get_files_from_filepath/<str:username>/", views.get_files_from_filepath, name="get_file_info_from_filepath"),
    path("paginated_get_files_info/<str:username>/", views.paginated_get_files_info, name="paginated_get_files_info"),
    path("getpartialfileinfo/<str:username>/",views.get_partial_file_info,name="getpartialfileinfo",),
    path("search_file/<str:username>/", views.search_file, name="search_file"),
    path("add_scanned_folder/<str:username>/", views.add_scanned_folder, name="add_scanned_folder"),
    path("remove_scanned_folder/<str:username>/", views.remove_scanned_folder, name="remove_scanned_folder"),
    path("get_scanned_folders/<str:username>/", views.get_scanned_folders, name="get_scanned_folders"),
]
