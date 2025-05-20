from django.urls import path
from . import views

urlpatterns = [

    path("add_device/<str:device_name>/", views.add_device_view, name="add_device"),
    path("delete_device/", views.delete_device, name="delete_device"),
    path("update_device_configurations/", views.update_device_configuration_preferences, name="update_devices"),
    path("getdeviceinfo/", views.getdeviceinfo, name="getdeviceinfo"),
    path("getonlinedevices/",views.handle_get_online_devices,name="getdeviceinfo",),
    path("declare_device_online/", views.declare_device_online, name="getdeviceinfo",),
    path("declare_device_offline/", views.declare_device_offline, name="getdeviceinfo"),
    path("get_single_device_info/<str:device_id>/", views.get_single_device_info, name="get_single_device_info"),
    path("get_single_device_info_with_device_name/<str:device_name>/", views.get_single_device_info_with_device_name, name="get_single_device_info_with_device_name"),
    path("add_downloaded_model/", views.add_downloaded_model, name="add_downloaded_model"),

]
