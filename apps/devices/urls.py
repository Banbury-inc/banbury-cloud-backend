from django.urls import path
from . import views

urlpatterns = [
    path("add_device/<str:username>/<str:device_name>/", views.add_device, name="add_device"),
    path("delete_device/<str:username>/", views.delete_device, name="delete_device"),
    path("update_device_configurations/<str:username>/", views.update_device_configuration_preferences, name="update_devices"),
    path("getdeviceinfo/<str:username>/", views.getdeviceinfo, name="getdeviceinfo"),
    path("getonlinedevices/<str:username>/",views.handle_get_online_devices,name="getdeviceinfo",),
    path("declare_device_online/<str:username>/", views.declare_device_online, name="getdeviceinfo",),
    path("declare_device_offline/<str:username>/", views.declare_device_offline, name="getdeviceinfo"),
]
