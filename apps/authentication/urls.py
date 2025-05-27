from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("login_api/", views.login_api, name="login_api"),
    path("register/",views.register, name="register"),
    path("new_register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/",views.new_register, name="new_register"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
    path("add_site_visitor_info/", views.add_site_visitor_info, name="get_site_visitor_info"),
    path("google/", views.google, name="google"),
    path("auth/callback", views.google_callback, name="google_callback_no_slash"),
    path("auth/callback/", views.google_callback, name="google_callback"),
    path("validate-token/", views.validate_token, name="validate_token"),
    path("refresh-token/", views.refresh_token, name="refresh_token"),
    path('api-key/generate/', views.generate_user_api_key, name='generate_api_key'),
    path('api-key/validate/', views.validate_user_api_key, name='validate_api_key'),
    path('api-key/list/', views.list_api_keys, name='list_api_keys'),
    path('api-key/delete/', views.delete_user_api_key, name='delete_api_key'),
]
