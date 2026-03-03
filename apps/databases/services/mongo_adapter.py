from typing import Any

from pymongo import MongoClient

from .serializers import serialize_value

SYSTEM_DATABASES = {"admin", "config", "local"}
MAX_DATABASES = 20
MAX_COLLECTIONS_PER_DATABASE = 500


def _connect(connection: dict[str, Any], database_override: str | None = None):
    database_name = database_override or connection.get("database")

    try:
        if connection.get("uri"):
            client = MongoClient(
                connection["uri"],
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
            return client, None

        client = MongoClient(
            host=connection["host"],
            port=connection["port"],
            username=connection["username"],
            password=connection["password"],
            authSource=database_name or "admin",
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        return client, None
    except Exception:
        return None, "Unable to connect to MongoDB"


def test_connection(connection: dict[str, Any]):
    client, error_message = _connect(connection)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        client.admin.command("ping")
        return {"success": True}
    except Exception:
        return {"success": False, "error": "MongoDB ping failed"}
    finally:
        client.close()


def get_tree(connection: dict[str, Any]):
    client, error_message = _connect(connection)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        if connection.get("database"):
            database_names = [connection["database"]]
        else:
            database_names = [db for db in client.list_database_names() if db not in SYSTEM_DATABASES][:MAX_DATABASES]

        tree = []
        for database_name in database_names:
            try:
                collections = client[database_name].list_collection_names()[:MAX_COLLECTIONS_PER_DATABASE]
            except Exception:
                collections = []

            tree.append(
                {
                    "id": f"mongo-db-{database_name}",
                    "label": database_name,
                    "nodeType": "database",
                    "database": database_name,
                    "hasChildren": True,
                    "children": [
                        {
                            "id": f"mongo-collection-{database_name}-{collection_name}",
                            "label": collection_name,
                            "nodeType": "collection",
                            "database": database_name,
                            "collection": collection_name,
                            "hasChildren": False,
                        }
                        for collection_name in collections
                    ],
                }
            )

        return {"success": True, "tree": tree}
    except Exception:
        return {"success": False, "error": "Failed to list MongoDB collections"}
    finally:
        client.close()


def get_table_data(connection: dict[str, Any], target: dict[str, Any], page: int, page_size: int):
    database_name = target["database"]
    collection_name = target["collection"]
    offset = (page - 1) * page_size

    client, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        collection = client[database_name][collection_name]
        total_count = collection.count_documents({}, maxTimeMS=10000)
        documents = list(
            collection.find({}, max_time_ms=10000).skip(offset).limit(page_size)
        )

        columns = []
        for document in documents:
            for key in document.keys():
                if key not in columns:
                    columns.append(key)

        rows = []
        for document in documents:
            rows.append({key: serialize_value(value) for key, value in document.items()})

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "page": page,
            "pageSize": page_size,
            "totalCount": total_count,
        }
    except Exception:
        return {"success": False, "error": "Failed to query MongoDB collection"}
    finally:
        client.close()
