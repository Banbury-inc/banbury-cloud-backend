from django.urls import path
from . import views

urlpatterns = [
    path('', views.flows_list, name='flows-list'),
    path('<str:flow_id>/', views.flow_detail, name='flow-detail'),
    path('<str:flow_id>/run/', views.flow_run, name='flow-run'),
    path('<str:flow_id>/schedule/', views.flow_schedule, name='flow-schedule'),
]
