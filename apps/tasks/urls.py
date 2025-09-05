from django.urls import path
from . import views
from . import taskstudio_views

urlpatterns = [
    # Existing session task endpoints
    path("add_task/", views.add_task, name="add_task"),
    path("update_task/", views.update_task, name="update_task"),
    path("fail_task/", views.fail_task, name="fail_task"),
    
    # TaskStudio task management endpoints
    path("taskstudio/", taskstudio_views.get_tasks, name="taskstudio_get_tasks"),
    path("taskstudio/create/", taskstudio_views.create_task, name="taskstudio_create_task"),
    path("taskstudio/<str:task_id>/", taskstudio_views.get_task, name="taskstudio_get_task"),
    path("taskstudio/<str:task_id>/update/", taskstudio_views.update_task, name="taskstudio_update_task"),
    path("taskstudio/<str:task_id>/delete/", taskstudio_views.delete_task, name="taskstudio_delete_task"),
    path("taskstudio/<str:task_id>/status/", taskstudio_views.update_task_status, name="taskstudio_update_status"),
    path("taskstudio/process-due/", taskstudio_views.process_due_tasks, name="taskstudio_process_due"),
]
