from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("login_api/", views.login_api, name="login_api"),
    path("register/",views.register, name="register"),
    path("new_register/<str:username>/<str:password>/<str:firstName>/<str:lastName>/",views.new_register, name="new_register"),
    path("getuserinfo4/<str:username>/<str:password>/", views.getuserinfo4, name="getuserinfo4"),
    path("add_site_visitor_info/", views.add_site_visitor_info, name="add_site_visitor_info"),
    path("get_site_visitor_info/", views.get_site_visitor_info, name="get_site_visitor_info"),
    path("google/", views.google, name="google"),
    path("auth/callback", views.google_callback, name="google_callback_no_slash"),
    path("auth/callback/", views.google_callback, name="google_callback"),
    path("validate-token/", views.validate_token, name="validate_token"),
    path("refresh-token/", views.refresh_token, name="refresh_token"),
    path('api-key/generate/', views.generate_user_api_key, name='generate_api_key'),
    path('api-key/validate/', views.validate_user_api_key, name='validate_api_key'),
    path('api-key/list/', views.list_api_keys, name='list_api_keys'),
    path('api-key/delete/', views.delete_user_api_key, name='delete_api_key'),
    # Gmail API proxy endpoints
    path('gmail/list_messages/', views.gmail_list_messages, name='gmail_list_messages'),
    path('gmail/messages/<str:message_id>/', views.gmail_get_message, name='gmail_get_message'),
    path('gmail/send_message/', views.gmail_send_message, name='gmail_send_message'),
    path('gmail/messages/<str:message_id>/modify/', views.gmail_modify_message, name='gmail_modify_message'),
    path('gmail/messages/batch', views.gmail_get_messages_batch, name='gmail_get_messages_batch'),
    path('gmail/messages/<str:message_id>/attachments/<str:attachment_id>', views.gmail_get_attachment, name='gmail_get_attachment'),
    path('gmail/test-batch', views.gmail_test_batch, name='gmail_test_batch'),
    # Gmail threading endpoints
    path('gmail/reply/', views.gmail_send_reply, name='gmail_send_reply'),
    path('gmail/thread/<str:thread_id>/', views.gmail_get_thread, name='gmail_get_thread'),
    path('gmail/threads/', views.gmail_list_threads, name='gmail_list_threads'),
    # Google Calendar API proxy endpoints
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('calendar/events/<str:event_id>/', views.calendar_event_detail, name='calendar_event_detail'),
    # Scope management endpoints
    path('scopes/user/', views.get_user_scopes, name='get_user_scopes'),
    path('scopes/request/', views.request_additional_scopes, name='request_additional_scopes'),
    path('scopes/features/', views.get_available_features, name='get_available_features'),
]
