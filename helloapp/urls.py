from django.urls import path
from helloapp import views


urlpatterns = [
    path('about/', views.aboutpage, name='about'),
    path('', views.homepage, name='home'),
    # path('register/', views.adduser, name='register'),
    path('login/', views.login, name='login'),
    path('get_neuranet_info/', views.get_neuranet_info, name='login'),
    path('login_api/', views.login_api, name='login_api'),
    # path('register/<str:firstName>/<str:lastName>/<str:username>/<str:password>/', views.registration_api, name='registration_api'),
    path('dashboard/<str:username>/', views.dashboard, name='dashboard'),
    path('update_profile/<str:username>/', views.update_user_profile, name='update_profile'),
    path('download-deb/', views.download_debian_package, name='download-deb'),
    path('getuserinfo/', views.getuserinfo, name='login'),
    path('getuserinfo2/<str:username>/', views.getuserinfo2, name='login'),
    path('get_small_user_info/<str:username>/', views.get_small_user_info, name='login'),
    path('getuserinfo3/<str:username>/<str:password>/', views.getuserinfo3, name='login'),
    path('update_devices/<str:username>/', views.update_devices, name='login'),
    path('add_device/<str:username>/<str:device_name>/', views.add_device, name='login'),
    path('register/<str:username>/<str:password>/<str:e>/<str:lastName>/', views.register, name='login'),
    path('new_register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/', views.new_register, name='login'),
    path('change_profile/<str:username>/<str:password>/<str:first_name>/<str:last_name>/<str:email>/', views.change_profile, name='login'),

]
