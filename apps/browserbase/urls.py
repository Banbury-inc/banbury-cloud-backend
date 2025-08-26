from django.urls import path
from . import views

urlpatterns = [
	path('session/', views.create_session, name='browserbase_create_session'),
	path('navigate/', views.navigate, name='browserbase_navigate'),
	path('click/', views.click, name='browserbase_click'),
	path('type/', views.type_text, name='browserbase_type'),
	path('screenshot/', views.screenshot, name='browserbase_screenshot'),
	path('content/', views.get_content, name='browserbase_content'),
	path('wait/', views.wait_for, name='browserbase_wait'),
	path('sessions/', views.list_sessions, name='browserbase_list_sessions'),
	path('check/', views.check_session, name='browserbase_check_session'),
]
