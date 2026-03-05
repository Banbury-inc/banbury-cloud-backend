import re
from typing import Any

ALLOWED_PROVIDERS = {"postgres", "mysql", "mongodb"}
ALLOWED_SSH_AUTH_METHODS = {"password", "publickey"}
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_\-.$]+$")
MAX_PAGE_SIZE = 200


def _is_valid_identifier(identifier: str) -> bool:
    if not identifier:
        return False
    return bool(IDENTIFIER_RE.fullmatch(identifier))


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


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
    raw_ssh = raw_connection.get("ssh")

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

    if raw_ssh is not None:
        if provider not in {"postgres", "mysql"}:
            return None, "SSH tunneling is supported only for PostgreSQL and MySQL"
        if not isinstance(raw_ssh, dict):
            return None, "Invalid SSH configuration"

        ssh_enabled = _normalize_bool(raw_ssh.get("enabled"))
        if ssh_enabled:
            ssh_host = str(raw_ssh.get("host", "")).strip()
            ssh_username = str(raw_ssh.get("username", "")).strip()
            ssh_password = str(raw_ssh.get("password", ""))
            ssh_private_key = str(raw_ssh.get("privateKey", ""))
            ssh_passphrase = str(raw_ssh.get("passphrase", ""))

            try:
                ssh_port = int(raw_ssh.get("port", 22))
            except (TypeError, ValueError):
                return None, "SSH port must be a number"

            if ssh_port <= 0 or ssh_port > 65535:
                return None, "SSH port must be between 1 and 65535"
            if not ssh_host:
                return None, "SSH host is required"
            if not ssh_username:
                return None, "SSH username is required"

            auth_method = str(raw_ssh.get("authMethod", "password")).strip().lower()
            if auth_method not in ALLOWED_SSH_AUTH_METHODS:
                return None, "Unsupported SSH authentication method"

            normalized_ssh = {
                "enabled": True,
                "host": ssh_host,
                "port": ssh_port,
                "username": ssh_username,
                "authMethod": "publicKey" if auth_method == "publickey" else "password",
            }

            if auth_method == "publickey":
                if not ssh_private_key:
                    return None, "SSH private key is required for public key authentication"
                normalized_ssh["privateKey"] = ssh_private_key
                if ssh_passphrase:
                    normalized_ssh["passphrase"] = ssh_passphrase
            else:
                if not ssh_password:
                    return None, "SSH password is required"
                normalized_ssh["password"] = ssh_password

            normalized["ssh"] = normalized_ssh

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


ALLOWED_FILTER_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "contains"}
MAX_FILTERS = 10


def normalize_order_by_payload(raw: Any):
    if raw is None:
        return None, None

    if not isinstance(raw, dict):
        return None, "orderBy must be an object"

    column = str(raw.get("column", "")).strip()
    direction = str(raw.get("direction", "")).strip().lower()

    if not column:
        return None, "orderBy.column is required"
    if not _is_valid_identifier(column):
        return None, "Invalid orderBy column identifier"
    if direction not in {"asc", "desc"}:
        return None, "orderBy.direction must be 'asc' or 'desc'"

    return {"column": column, "direction": direction}, None


def normalize_filters_payload(raw: Any):
    if raw is None:
        return [], None

    if not isinstance(raw, list):
        return None, "filters must be an array"

    if len(raw) > MAX_FILTERS:
        return None, f"Too many filters (max {MAX_FILTERS})"

    normalized = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            return None, f"Filter {i} must be an object"

        column = str(item.get("column", "")).strip()
        operator = str(item.get("operator", "")).strip()
        value = item.get("value")

        if not column:
            return None, f"Filter {i}: column is required"
        if not _is_valid_identifier(column):
            return None, f"Filter {i}: invalid column identifier"
        if operator not in ALLOWED_FILTER_OPERATORS:
            return None, f"Filter {i}: unsupported operator '{operator}'"
        if value is None:
            return None, f"Filter {i}: value is required"

        normalized.append({"column": column, "operator": operator, "value": str(value)})

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
