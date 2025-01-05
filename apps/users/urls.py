from django.urls import path
from . import views

urlpatterns = [
    path("getuserinfo/<str:username>/", views.getuserinfo, name="getuserinfo"),
    path("getuserinfo2/<str:username>/", views.getuserinfo2, name="getuserinfo2"),
    path("get_small_user_info/<str:username>/", views.get_small_user_info, name="get_small_user_info"),
    path("getuserinfo3/<str:username>/<str:password>/", views.getuserinfo3, name="getuserinfo3"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
    path("update_profile/", views.update_user_profile, name="update_profile"),
    path("change_profile/<str:username>/<str:password>/<str:first_name>/<str:last_name>/<str:email>/",views.change_profile, name="change_profile"),
    path("get_profile_picture/<str:username>/", views.get_profile_picture, name="get_profile_picture"),
]
