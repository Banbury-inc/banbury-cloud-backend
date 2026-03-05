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


def _build_mongo_query(filters: list[dict]) -> dict:
    if not filters:
        return {}

    operator_map = {
        "=": "$eq",
        "!=": "$ne",
        ">": "$gt",
        "<": "$lt",
        ">=": "$gte",
        "<=": "$lte",
    }

    query: dict[str, Any] = {}
    for f in filters:
        col = f["column"]
        op = f["operator"]
        val = f["value"]

        if op == "contains":
            condition = {"$regex": val, "$options": "i"}
        else:
            mongo_op = operator_map[op]
            condition = {mongo_op: val}

        if col in query:
            query[col].update(condition)
        else:
            query[col] = condition

    return query


def get_table_data(connection: dict[str, Any], target: dict[str, Any], page: int, page_size: int, order_by=None, filters=None):
    database_name = target["database"]
    collection_name = target["collection"]
    offset = (page - 1) * page_size

    client, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        import pymongo

        collection = client[database_name][collection_name]
        query = _build_mongo_query(filters or [])
        total_count = collection.count_documents(query, maxTimeMS=10000)

        cursor = collection.find(query, max_time_ms=10000).skip(offset).limit(page_size)
        if order_by:
            direction = pymongo.ASCENDING if order_by["direction"] == "asc" else pymongo.DESCENDING
            cursor = cursor.sort(order_by["column"], direction)

        documents = list(cursor)

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
            "primaryKeyColumns": ["_id"],
        }
    except Exception:
        return {"success": False, "error": "Failed to query MongoDB collection"}
    finally:
        client.close()


def _parse_id(value):
    from bson import ObjectId
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except Exception:
            return value
    return value


def update_rows(connection: dict[str, Any], target: dict[str, Any], updates: list[dict]):
    database_name = target["database"]
    collection_name = target["collection"]

    client, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        collection = client[database_name][collection_name]
        for update in updates:
            primary_key = update.get("primaryKey", {})
            changes = update.get("changes", {})
            if not primary_key or not changes:
                continue
            query = {k: (_parse_id(v) if k == "_id" else v) for k, v in primary_key.items()}
            collection.update_one(query, {"$set": changes})
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Failed to update MongoDB documents"}
    finally:
        client.close()


def insert_rows(connection: dict[str, Any], target: dict[str, Any], rows: list[dict]):
    database_name = target["database"]
    collection_name = target["collection"]

    client, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        collection = client[database_name][collection_name]
        filtered_rows = [row for row in rows if row]
        if filtered_rows:
            collection.insert_many(filtered_rows)
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Failed to insert documents into MongoDB collection"}
    finally:
        client.close()
