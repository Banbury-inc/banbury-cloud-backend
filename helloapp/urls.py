from django.urls import path
from helloapp import views


urlpatterns = [
    path('about/', views.aboutpage, name='about'),
    path('', views.homepage, name='home'),
    path('add_user/', views.adduser, name='add_user'),

]