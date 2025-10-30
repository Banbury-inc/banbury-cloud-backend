from django.urls import path
from . import views

urlpatterns = [
    path("getfrienduserinfo/<str:friend_username>/", views.getfrienduserinfo, name="getuserinfo"),
    path("getuserinfo2/", views.getuserinfo2, name="getuserinfo2"),
    path("get_small_user_info/", views.get_small_user_info, name="get_small_user_info"),
    path("getuserinfo3/<str:password>/", views.getuserinfo3, name="getuserinfo3"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
    path("update_profile/", views.update_user_profile, name="update_profile"),
    path("change_profile/<str:password>/<str:first_name>/<str:last_name>/<str:email>/",views.change_profile, name="change_profile"),
    path("get_profile_picture/", views.get_profile_picture, name="get_profile_picture"),
    path("typeahead/<str:search>/", views.typeahead, name="typeahead"),
    path("ai_message_sent/", views.ai_message_sent, name="ai_message_sent"),
    path("track_dashboard_visit/", views.track_dashboard_visit, name="track_dashboard_visit"),
    path("track_workspace_visit/", views.track_workspace_visit, name="track_workspace_visit"),
    path("list_all_users/", views.list_all_users, name="list_all_users"),
    path("send_friend_request/", views.send_friend_request, name="send_friend_request"),
    path("remove_friend/", views.remove_friend, name="remove_friend"),
    path("get_friends/", views.get_friends, name="get_friends"),
    path("get_friend_requests/", views.get_friend_requests, name="get_friend_requests"),
    path("accept_friend_request/", views.accept_friend_request, name="accept_friend_request"),
    path("reject_friend_request/", views.reject_friend_request, name="reject_friend_request"),
    path("get_user_friends/", views.get_user_friends, name="get_user_friends"),
    path("get_realtime_token/", views.get_realtime_token, name="get_realtime_token"),
]
