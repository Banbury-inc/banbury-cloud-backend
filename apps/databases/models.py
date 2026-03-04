from pymongo.mongo_client import MongoClient
from datetime import datetime
import uuid
import os

uri = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
)
client = MongoClient(uri)
db = client["NeuraNet"]

saved_connections_collection = db["saved_database_connections"]


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in ("created_at", "updated_at"):
        if field in doc and hasattr(doc[field], "isoformat"):
            doc[field] = doc[field].isoformat()
    return doc


class SavedDatabaseConnection:
    @staticmethod
    def create(username: str, name: str, config: dict) -> dict:
        connection_id = f"{config.get('provider')}-{config.get('host')}-{config.get('port')}-{config.get('database', '')}"
        existing = saved_connections_collection.find_one({"id": connection_id, "username": username})
        if existing:
            saved_connections_collection.update_one(
                {"id": connection_id, "username": username},
                {"$set": {"name": name, "config": config, "updated_at": datetime.utcnow()}},
            )
            doc = saved_connections_collection.find_one({"id": connection_id, "username": username})
            return _serialize(dict(doc))

        doc = {
            "id": connection_id,
            "username": username,
            "name": name,
            "config": config,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        saved_connections_collection.insert_one(doc)
        return _serialize(dict(doc))

    @staticmethod
    def list_for_user(username: str) -> list:
        docs = list(
            saved_connections_collection.find({"username": username}).sort("updated_at", -1)
        )
        return [_serialize(d) for d in docs]

    @staticmethod
    def delete(connection_id: str, username: str) -> bool:
        result = saved_connections_collection.delete_one({"id": connection_id, "username": username})
        return result.deleted_count > 0
