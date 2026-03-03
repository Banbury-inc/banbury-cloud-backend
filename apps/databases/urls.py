from django.urls import path

from . import views

urlpatterns = [
    path("connections/test/", views.test_connection, name="databases_test_connection"),
    path("tree/", views.get_tree, name="databases_get_tree"),
    path("table-data/", views.get_table_data, name="databases_get_table_data"),
]
