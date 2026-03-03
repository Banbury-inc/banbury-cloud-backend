from . import mongo_adapter, mysql_adapter, postgres_adapter


def _get_adapter(provider: str):
    adapter_map = {
        "postgres": postgres_adapter,
        "mysql": mysql_adapter,
        "mongodb": mongo_adapter,
    }
    return adapter_map.get(provider)


def test_database_connection(connection: dict):
    adapter = _get_adapter(connection["provider"])
    if adapter is None:
        return {"success": False, "error": "Unsupported provider"}
    return adapter.test_connection(connection)


def get_tree_for_connection(connection: dict):
    adapter = _get_adapter(connection["provider"])
    if adapter is None:
        return {"success": False, "error": "Unsupported provider"}
    return adapter.get_tree(connection)


def get_table_data_for_connection(connection: dict, target: dict, page: int, page_size: int):
    adapter = _get_adapter(connection["provider"])
    if adapter is None:
        return {"success": False, "error": "Unsupported provider"}
    return adapter.get_table_data(connection, target, page, page_size)
