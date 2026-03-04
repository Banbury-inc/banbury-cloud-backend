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

flows_collection = db["flows"]


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in ("created_at", "updated_at", "last_run_at"):
        if field in doc and hasattr(doc[field], "isoformat"):
            doc[field] = doc[field].isoformat()
    return doc


class Flow:
    @staticmethod
    def create(username: str, name: str) -> dict:
        flow = {
            "id": str(uuid.uuid4()),
            "username": username,
            "name": name,
            "graph_json": {"nodes": [], "edges": [], "viewport": None},
            "last_run_status": None,
            "last_run_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        flows_collection.insert_one(flow)
        return _serialize(dict(flow))

    @staticmethod
    def list_for_user(username: str) -> list:
        docs = list(
            flows_collection.find({"username": username}).sort("updated_at", -1)
        )
        return [_serialize(d) for d in docs]

    @staticmethod
    def get(flow_id: str, username: str) -> dict | None:
        doc = flows_collection.find_one({"id": flow_id, "username": username})
        if doc is None:
            return None
        return _serialize(doc)

    @staticmethod
    def update(flow_id: str, username: str, updates: dict) -> dict | None:
        updates["updated_at"] = datetime.utcnow()
        result = flows_collection.update_one(
            {"id": flow_id, "username": username}, {"$set": updates}
        )
        if result.matched_count == 0:
            return None
        return Flow.get(flow_id, username)

    @staticmethod
    def delete(flow_id: str, username: str) -> bool:
        result = flows_collection.delete_one({"id": flow_id, "username": username})
        return result.deleted_count > 0
