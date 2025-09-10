from django.urls import path
from . import views

urlpatterns = [
    # Platform management
    path('platforms/', views.get_platforms, name='get_platforms'),
    path('platforms/<str:platform_id>/test-auth/', views.test_platform_auth, name='test_platform_auth'),
    
    # Session management
    path('sessions/', views.get_meeting_sessions, name='get_meeting_sessions'),
    path('sessions/<str:session_id>/', views.get_meeting_session, name='get_meeting_session'),
    path('sessions/join/', views.join_meeting, name='join_meeting'),
    path('sessions/<str:session_id>/leave/', views.leave_meeting, name='leave_meeting'),
    path('sessions/<str:session_id>/transcription/', views.get_transcription, name='get_transcription'),
    path('sessions/<str:session_id>/summary/', views.meeting_summary, name='meeting_summary'),
    path('sessions/<str:session_id>/recording/download/', views.download_recording, name='download_recording'),
    path('sessions/<str:session_id>/delete/', views.delete_meeting_session, name='delete_meeting_session'),
    
    # Alternative shorter paths for easier frontend access
    path('join/', views.join_meeting, name='join_meeting_short'),
    path('leave/<str:session_id>/', views.leave_meeting, name='leave_meeting_short'),
    
    # Configuration
    path('config/', views.agent_config, name='agent_config'),
    
    # System status
    path('status/', views.agent_status, name='agent_status'),
    
    # Recall AI bot management
    path('recall-bot/create/', views.create_recall_bot, name='create_recall_bot'),
    path('recall-bot/<str:bot_id>/', views.get_recall_bot, name='get_recall_bot'),
    path('recall-bot/<str:bot_id>/stop/', views.stop_recall_bot, name='stop_recall_bot'),
    
    # Recall AI webhooks
    path('recall-webhook/', views.recall_webhook, name='recall_webhook'),
    
    # Debug endpoints
    path('debug/create-transcript/<str:recording_id>/', views.debug_create_transcript, name='debug_create_transcript'),
    path('debug/get-transcript/<str:transcript_id>/', views.debug_get_transcript, name='debug_get_transcript'),
    path('debug/bot-recordings/<str:bot_id>/', views.debug_bot_recordings, name='debug_bot_recordings'),
]