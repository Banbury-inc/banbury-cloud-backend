from datetime import datetime, timezone
import uuid

from core.mongodb_manager import get_mongodb_collection

map_places_collection = get_mongodb_collection("map_places")

DATETIME_FIELDS = ("created_at", "last_visited_at")

MAX_RECENT_PLACES = 30


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in DATETIME_FIELDS:
        if field in doc and hasattr(doc[field], "isoformat"):
            doc[field] = doc[field].isoformat()
    return doc


class MapPlace:
    @staticmethod
    def list_for_user(username: str) -> list:
        docs = list(
            map_places_collection.find({"username": username}).sort("last_visited_at", -1)
        )
        return [_serialize(d) for d in docs]

    @staticmethod
    def get(place_id: str, username: str) -> dict | None:
        doc = map_places_collection.find_one({"id": place_id, "username": username})
        if doc is None:
            return None
        return _serialize(doc)

    @staticmethod
    def upsert_recent(
        username: str,
        name: str,
        longitude: float,
        latitude: float,
        zoom: float,
    ) -> dict:
        """Insert a visited place or bump its last_visited_at if a matching place exists."""
        now = datetime.now(timezone.utc)
        existing = map_places_collection.find_one(
            {
                "username": username,
                "longitude": longitude,
                "latitude": latitude,
            }
        )

        if existing is not None:
            map_places_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {"last_visited_at": now, "name": name, "zoom": zoom}},
            )
            MapPlace._trim_recents(username)
            return MapPlace.get(existing["id"], username)

        place = {
            "id": str(uuid.uuid4()),
            "username": username,
            "name": name,
            "longitude": longitude,
            "latitude": latitude,
            "zoom": zoom,
            "is_favorite": False,
            "last_visited_at": now,
            "created_at": now,
        }
        map_places_collection.insert_one(place)
        MapPlace._trim_recents(username)
        return _serialize(dict(place))

    @staticmethod
    def _trim_recents(username: str) -> None:
        """Keep only the most recent non-favorite places up to MAX_RECENT_PLACES."""
        recents = list(
            map_places_collection.find(
                {"username": username, "is_favorite": {"$ne": True}}
            ).sort("last_visited_at", -1)
        )
        for stale in recents[MAX_RECENT_PLACES:]:
            map_places_collection.delete_one({"_id": stale["_id"]})

    @staticmethod
    def update(place_id: str, username: str, updates: dict) -> dict | None:
        result = map_places_collection.update_one(
            {"id": place_id, "username": username}, {"$set": updates}
        )
        if result.matched_count == 0:
            return None
        return MapPlace.get(place_id, username)

    @staticmethod
    def delete(place_id: str, username: str) -> bool:
        result = map_places_collection.delete_one({"id": place_id, "username": username})
        return result.deleted_count > 0
