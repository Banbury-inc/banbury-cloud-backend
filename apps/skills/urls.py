from django.urls import path

from . import views


urlpatterns = [
    path("", views.skills_list, name="skills-list"),
    path("<str:skill_id>/", views.skill_detail, name="skill-detail"),
]
