from django.urls import path

from . import views

urlpatterns = [
    path("connections/test/", views.test_connection, name="databases_test_connection"),
    path("connections/", views.list_connections, name="databases_list_connections"),
    path("connections/save/", views.save_connection, name="databases_save_connection"),
    path("connections/<str:connection_id>/", views.delete_connection, name="databases_delete_connection"),
    path("tree/", views.get_tree, name="databases_get_tree"),
    path("table-data/", views.get_table_data, name="databases_get_table_data"),
]
