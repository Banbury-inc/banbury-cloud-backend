from django.urls import path
from . import views

urlpatterns = [
    path("getuserinfo/<str:username>/", views.getuserinfo, name="getuserinfo"),
    path("getuserinfo2/<str:username>/", views.getuserinfo2, name="getuserinfo2"),
    path("get_small_user_info/<str:username>/", views.get_small_user_info, name="get_small_user_info"),
    path("getuserinfo3/<str:username>/<str:password>/", views.getuserinfo3, name="getuserinfo3"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
]
