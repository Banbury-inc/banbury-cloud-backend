from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .handlers.request_handlers import (
    handle_delete_connection_request,
    handle_get_table_data_request,
    handle_get_tree_request,
    handle_insert_rows_request,
    handle_list_connections_request,
    handle_save_connection_request,
    handle_test_connection_request,
    handle_update_rows_request,
)


@csrf_exempt
@require_http_methods(["POST"])
def test_connection(request):
    return handle_test_connection_request(request)


@csrf_exempt
@require_http_methods(["POST"])
def get_tree(request):
    return handle_get_tree_request(request)


@csrf_exempt
@require_http_methods(["POST"])
def get_table_data(request):
    return handle_get_table_data_request(request)


@csrf_exempt
@require_http_methods(["POST"])
def update_rows(request):
    return handle_update_rows_request(request)


@csrf_exempt
@require_http_methods(["POST"])
def insert_rows(request):
    return handle_insert_rows_request(request)


@csrf_exempt
@require_http_methods(["POST"])
def save_connection(request):
    return handle_save_connection_request(request)


@csrf_exempt
@require_http_methods(["GET"])
def list_connections(request):
    return handle_list_connections_request(request)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_connection(request, connection_id: str):
    return handle_delete_connection_request(request, connection_id)
