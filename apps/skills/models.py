from datetime import datetime
import re
import uuid

from core.mongodb_manager import get_mongodb_collection


skills_collection = get_mongodb_collection("user_skills")

DATETIME_FIELDS = ("created_at", "updated_at")


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in DATETIME_FIELDS:
        if field in doc and hasattr(doc[field], "isoformat"):
            doc[field] = doc[field].isoformat()
    return doc


def parse_skill_metadata(content: str) -> dict:
    metadata = {"name": "", "description": ""}
    text = content or ""

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" not in line:
                    continue

                key, value = line.split(":", 1)
                normalized_key = key.strip().lower()
                if normalized_key in metadata:
                    metadata[normalized_key] = value.strip().strip('"').strip("'")

    if not metadata["name"]:
        heading = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        if heading:
            metadata["name"] = heading.group(1).strip()

    if not metadata["description"]:
        description = re.search(r"^description:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
        if description:
            metadata["description"] = description.group(1).strip().strip('"').strip("'")

    return metadata


class Skill:
    @staticmethod
    def create(username: str, content: str, enabled: bool = True) -> dict:
        metadata = parse_skill_metadata(content)
        now = datetime.utcnow()
        skill = {
            "id": str(uuid.uuid4()),
            "username": username,
            "name": metadata["name"] or "Untitled Skill",
            "description": metadata["description"],
            "content": content,
            "enabled": enabled,
            "created_at": now,
            "updated_at": now,
        }
        skills_collection.insert_one(skill)
        return _serialize(dict(skill))

    @staticmethod
    def list_for_user(username: str) -> list:
        docs = list(skills_collection.find({"username": username}).sort("updated_at", -1))
        return [_serialize(doc) for doc in docs]

    @staticmethod
    def get(skill_id: str, username: str) -> dict | None:
        doc = skills_collection.find_one({"id": skill_id, "username": username})
        if doc is None:
            return None
        return _serialize(doc)

    @staticmethod
    def update(skill_id: str, username: str, updates: dict) -> dict | None:
        allowed_updates = {}
        if "content" in updates:
            allowed_updates["content"] = updates["content"]
            metadata = parse_skill_metadata(updates["content"])
            allowed_updates["name"] = metadata["name"] or "Untitled Skill"
            allowed_updates["description"] = metadata["description"]
        if "enabled" in updates:
            allowed_updates["enabled"] = bool(updates["enabled"])

        if not allowed_updates:
            return Skill.get(skill_id, username)

        allowed_updates["updated_at"] = datetime.utcnow()
        result = skills_collection.update_one(
            {"id": skill_id, "username": username},
            {"$set": allowed_updates},
        )
        if result.matched_count == 0:
            return None
        return Skill.get(skill_id, username)

    @staticmethod
    def delete(skill_id: str, username: str) -> bool:
        result = skills_collection.delete_one({"id": skill_id, "username": username})
        return result.deleted_count > 0
