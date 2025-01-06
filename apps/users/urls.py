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
    path("typeahead/<str:search>/", views.typeahead, name="typeahead"),
    path("send_friend_request/", views.send_friend_request, name="send_friend_request"),
    path("remove_friend/", views.remove_friend, name="remove_friend"),
    path("get_friends/<str:username>/", views.get_friends, name="get_friends"),
    path("get_friend_requests/<str:username>/", views.get_friend_requests, name="get_friend_requests"),
    path("accept_friend_request/", views.accept_friend_request, name="accept_friend_request"),
    path("reject_friend_request/", views.reject_friend_request, name="reject_friend_request"),
]