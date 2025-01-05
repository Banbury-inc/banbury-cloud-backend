from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("login_api/", views.login_api, name="login_api"),
    path("register/<str:username>/<str:password>/<str:e>/<str:lastName>/",views.register, name="register"),
    path("new_register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/",views.new_register, name="new_register"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
    path("add_site_visitor_info/", views.add_site_visitor_info, name="get_site_visitor_info"),
    path("google/", views.google, name="google"),
    path("auth/callback/", views.google_callback, name="google_callback"),
]
