from django.urls import path
from helloapp import views


urlpatterns = [
    path('about/', views.aboutpage, name='about'),
    path('', views.homepage, name='home'),
    path('register/', views.adduser, name='register'),
    path('login/', views.login, name='login'),
    path('dashboard/<str:username>/', views.dashboard, name='dashboard'),
    path('update_profile/<str:username>/', views.update_user_profile, name='update_profile'),

]