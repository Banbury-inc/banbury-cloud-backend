from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .handlers.request_handlers import (
    handle_get_table_data_request,
    handle_get_tree_request,
    handle_test_connection_request,
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
