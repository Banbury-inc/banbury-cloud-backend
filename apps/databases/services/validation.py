import re
from typing import Any

ALLOWED_PROVIDERS = {"postgres", "mysql", "mongodb"}
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_\-.$]+$")
MAX_PAGE_SIZE = 200


def _is_valid_identifier(identifier: str) -> bool:
    if not identifier:
        return False
    return bool(IDENTIFIER_RE.fullmatch(identifier))


def normalize_connection_payload(raw_connection: Any):
    if not isinstance(raw_connection, dict):
        return None, "Missing connection payload"

    provider = str(raw_connection.get("provider", "")).strip().lower()
    uri = str(raw_connection.get("uri", "")).strip()
    host = str(raw_connection.get("host", "")).strip()
    username = str(raw_connection.get("username", "")).strip()
    password = str(raw_connection.get("password", ""))
    database = raw_connection.get("database")
    database_name = str(database).strip() if database is not None else ""

    if provider not in ALLOWED_PROVIDERS:
        return None, "Unsupported provider"

    if provider == "mongodb" and uri:
        normalized = {
            "provider": provider,
            "uri": uri,
        }
        if database_name:
            if not _is_valid_identifier(database_name):
                return None, "Invalid database name format"
            normalized["database"] = database_name
        return normalized, None

    if not host:
        return None, "Host is required"
    if not username:
        return None, "Username is required"
    if not password:
        return None, "Password is required"

    try:
        port = int(raw_connection.get("port"))
    except (TypeError, ValueError):
        return None, "Port must be a number"

    if port <= 0 or port > 65535:
        return None, "Port must be between 1 and 65535"

    if database_name and not _is_valid_identifier(database_name):
        return None, "Invalid database name format"

    normalized = {
        "provider": provider,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
    }
    if database_name:
        normalized["database"] = database_name

    return normalized, None


def normalize_target_payload(provider: str, raw_target: Any):
    if not isinstance(raw_target, dict):
        return None, "Missing target payload"

    database = str(raw_target.get("database", "")).strip()
    schema = str(raw_target.get("schema", "")).strip()
    table = str(raw_target.get("table", "")).strip()
    collection = str(raw_target.get("collection", "")).strip()

    if not database:
        return None, "Target database is required"
    if not _is_valid_identifier(database):
        return None, "Invalid database identifier"

    if provider in {"postgres", "mysql"}:
        if not table:
            return None, "Target table is required"
        if not _is_valid_identifier(table):
            return None, "Invalid table identifier"
        if schema and not _is_valid_identifier(schema):
            return None, "Invalid schema identifier"

    if provider == "mongodb":
        if not collection:
            return None, "Target collection is required"
        if not _is_valid_identifier(collection):
            return None, "Invalid collection identifier"

    normalized = {"database": database}
    if schema:
        normalized["schema"] = schema
    if table:
        normalized["table"] = table
    if collection:
        normalized["collection"] = collection
    return normalized, None


def normalize_page_payload(raw_page: Any, raw_page_size: Any):
    page = 1 if raw_page is None else raw_page
    page_size = 50 if raw_page_size is None else raw_page_size

    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError):
        return 1, 50, "Page and pageSize must be numbers"

    if page <= 0:
        return 1, 50, "Page must be at least 1"
    if page_size <= 0:
        return 1, 50, "Page size must be at least 1"
    if page_size > MAX_PAGE_SIZE:
        return 1, 50, f"Page size must be <= {MAX_PAGE_SIZE}"

    return page, page_size, None
