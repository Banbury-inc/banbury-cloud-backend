from django.urls import path
from helloapp import views


urlpatterns = [
    path('about/', views.aboutpage, name='about'),
    path('', views.homepage, name='home'),
    path('register/', views.adduser, name='register'),
    path('login/', views.login, name='login'),
    path('login_api/', views.login_api, name='login_api'),
    path('register/<str:firstName>/<str:lastName>/<str:username>/<str:password>/', views.registration_api, name='registration_api'),
    path('dashboard/<str:username>/', views.dashboard, name='dashboard'),
    path('update_profile/<str:username>/', views.update_user_profile, name='update_profile'),
    path('download-deb/', views.download_debian_package, name='download-deb'),
    path('getuserinfo/', views.getuserinfo, name='login'),
    path('getuserinfo2/<str:username>/', views.getuserinfo2, name='login'),
    path('getuserinfo3/<str:username>/<str:password>/', views.getuserinfo3, name='login'),
    path('register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/', views.register, name='login'),

]
