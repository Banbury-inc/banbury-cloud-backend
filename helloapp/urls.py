from django.urls import path
from helloapp import views
from helloapp import consumers  # Make sure this matches the actual name

urlpatterns = [
    # Ping
    path("ping/", views.ping, name="home"),
    # Home and About pages
    path("", views.homepage, name="home"),
    path("about/", views.aboutpage, name="about"),
    # Authentication and Registration
    path("login/", views.login, name="login"),
    path("login_api/", views.login_api, name="login_api"),
    path("register/<str:username>/<str:password>/<str:e>/<str:lastName>/",views.register, name="register"),
    path("new_register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/",views.new_register, name="new_register"),
    # Profile Management
    path("update_profile/<str:username>/", views.update_user_profile, name="update_profile"),
    path("change_profile/<str:username>/<str:password>/<str:first_name>/<str:last_name>/<str:email>/",views.change_profile, name="change_profile"),
    # Dashboard and Session Management
    path("dashboard/<str:username>/", views.dashboard, name="dashboard"),
    path("get_session/<str:username>/", views.get_session, name="get_session"),
    path("get_recent_session/<str:username>/", views.get_recent_session, name="get_session"),
    # User Information
    path("getuserinfo/<str:username>/", views.getuserinfo, name="getuserinfo"),
    path("getuserinfo2/<str:username>/", views.getuserinfo2, name="getuserinfo2"),
    path("get_small_user_info/<str:username>/", views.get_small_user_info, name="get_small_user_info"),
    path("getuserinfo3/<str:username>/<str:password>/", views.getuserinfo3, name="getuserinfo3"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
    # NeuraNet and Visitor Info
    path("get_neuranet_info/", views.get_neuranet_info, name="get_neuranet_info"),
    path("add_site_visitor_info/", views.add_site_visitor_info, name="add_site_visitor_info"),
    # Device and File Management
    path("add_device/<str:username>/<str:device_name>/", views.add_device, name="add_device"),
    path("delete_device/<str:username>/", views.delete_device, name="delete_device"),
    path("update_devices/<str:username>/", views.update_devices, name="update_devices"),
    path("getdeviceinfo/<str:username>/", views.getdeviceinfo, name="getdeviceinfo"),
    path("getonlinedevices/<str:username>/",views.handle_get_online_devices,name="getdeviceinfo",),
    path("declare_device_online/<str:username>/", views.declare_device_online, name="getdeviceinfo",),
    path("declare_device_offline/<str:username>/", views.declare_device_offline, name="getdeviceinfo"),
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
    # Prediction Service
    path("run_pipeline/<str:username>/", views.run_pipeline, name="run_pipeline"),
    path("add_file_to_sync/<str:username>/", views.add_file_to_sync, name="add_file_to_sync"),
    # Task Management
    path("add_task/<str:username>/", views.add_task, name="add_task"),
    path("update_task/<str:username>/", views.update_task, name="update_task"),
    path("fail_task/<str:username>/", views.fail_task, name="update_task"),
    # Settings and Package Downloads
    path("update_settings/<str:username>/", views.update_settings, name="update_settings"),
    # path('download-deb/', views.download_debian_package, name='download_deb'),
]
