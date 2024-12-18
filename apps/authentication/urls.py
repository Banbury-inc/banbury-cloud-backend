from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("login_api/", views.login_api, name="login_api"),
    path("register/<str:username>/<str:password>/<str:e>/<str:lastName>/",views.register, name="register"),
    path("new_register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/",views.new_register, name="new_register"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
]
