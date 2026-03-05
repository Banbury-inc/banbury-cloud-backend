import json
from typing import Any

from django.http import JsonResponse

from ..models import SavedDatabaseConnection
from ..services.database_service import (
    get_table_data_for_connection,
    get_tree_for_connection,
    insert_rows_for_connection,
    test_database_connection,
    update_rows_for_connection,
)
from ..services.validation import normalize_connection_payload, normalize_filters_payload, normalize_order_by_payload, normalize_page_payload, normalize_target_payload


def _parse_request_json(request) -> dict[str, Any]:
    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        payload = json.loads(body or "{}")
        if isinstance(payload, dict):
            return payload
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return {}


def _ensure_authenticated(request):
    username = getattr(request, "username_from_token", None)
    if username:
        return None
    return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)


def handle_test_connection_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    payload = _parse_request_json(request)
    connection, error_message = normalize_connection_payload(payload.get("connection"))
    if error_message:
        return JsonResponse({"success": False, "error": error_message}, status=400)

    result = test_database_connection(connection)
    status_code = 200 if result.get("success") else 400
    return JsonResponse(result, status=status_code)


def handle_get_tree_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    payload = _parse_request_json(request)
    connection, error_message = normalize_connection_payload(payload.get("connection"))
    if error_message:
        return JsonResponse({"success": False, "error": error_message}, status=400)

    result = get_tree_for_connection(connection)
    status_code = 200 if result.get("success") else 400
    return JsonResponse(result, status=status_code)


def handle_get_table_data_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    payload = _parse_request_json(request)
    connection, connection_error = normalize_connection_payload(payload.get("connection"))
    if connection_error:
        return JsonResponse({"success": False, "error": connection_error}, status=400)

    target, target_error = normalize_target_payload(connection["provider"], payload.get("target"))
    if target_error:
        return JsonResponse({"success": False, "error": target_error}, status=400)

    page, page_size, page_error = normalize_page_payload(payload.get("page"), payload.get("pageSize"))
    if page_error:
        return JsonResponse({"success": False, "error": page_error}, status=400)

    order_by, order_by_error = normalize_order_by_payload(payload.get("orderBy"))
    if order_by_error:
        return JsonResponse({"success": False, "error": order_by_error}, status=400)

    filters, filters_error = normalize_filters_payload(payload.get("filters"))
    if filters_error:
        return JsonResponse({"success": False, "error": filters_error}, status=400)

    result = get_table_data_for_connection(connection, target, page, page_size, order_by=order_by, filters=filters)
    status_code = 200 if result.get("success") else 400
    return JsonResponse(result, status=status_code)


def handle_update_rows_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    payload = _parse_request_json(request)
    connection, connection_error = normalize_connection_payload(payload.get("connection"))
    if connection_error:
        return JsonResponse({"success": False, "error": connection_error}, status=400)

    target, target_error = normalize_target_payload(connection["provider"], payload.get("target"))
    if target_error:
        return JsonResponse({"success": False, "error": target_error}, status=400)

    updates = payload.get("updates")
    if not isinstance(updates, list):
        return JsonResponse({"success": False, "error": "updates must be a list"}, status=400)

    result = update_rows_for_connection(connection, target, updates)
    status_code = 200 if result.get("success") else 400
    return JsonResponse(result, status=status_code)


def handle_insert_rows_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    payload = _parse_request_json(request)
    connection, connection_error = normalize_connection_payload(payload.get("connection"))
    if connection_error:
        return JsonResponse({"success": False, "error": connection_error}, status=400)

    target, target_error = normalize_target_payload(connection["provider"], payload.get("target"))
    if target_error:
        return JsonResponse({"success": False, "error": target_error}, status=400)

    rows = payload.get("rows")
    if not isinstance(rows, list):
        return JsonResponse({"success": False, "error": "rows must be a list"}, status=400)

    result = insert_rows_for_connection(connection, target, rows)
    status_code = 200 if result.get("success") else 400
    return JsonResponse(result, status=status_code)


def handle_save_connection_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    username = request.username_from_token
    payload = _parse_request_json(request)
    name = payload.get("name")
    config = payload.get("config")

    if not name or not config:
        return JsonResponse({"success": False, "error": "name and config are required"}, status=400)

    saved = SavedDatabaseConnection.create(username, name, config)
    return JsonResponse({"success": True, "connection": saved})


def handle_list_connections_request(request):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    username = request.username_from_token
    connections = SavedDatabaseConnection.list_for_user(username)
    return JsonResponse({"success": True, "connections": connections})


def handle_delete_connection_request(request, connection_id: str):
    auth_error = _ensure_authenticated(request)
    if auth_error:
        return auth_error

    username = request.username_from_token
    deleted = SavedDatabaseConnection.delete(connection_id, username)
    if not deleted:
        return JsonResponse({"success": False, "error": "Connection not found"}, status=404)
    return JsonResponse({"success": True})
