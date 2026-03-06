from pymongo.mongo_client import MongoClient
from datetime import datetime, timezone, timedelta
import uuid
import os

uri = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
)
client = MongoClient(uri)
db = client["NeuraNet"]

flows_collection = db["flows"]
users_collection = db["users"]

DATETIME_FIELDS = (
    "created_at", "updated_at", "last_run_at",
    "schedule_next_run", "schedule_end_date", "schedule_last_triggered",
)


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in DATETIME_FIELDS:
        if field in doc and hasattr(doc[field], "isoformat"):
            doc[field] = doc[field].isoformat()
    return doc


def compute_next_run(
    pattern: str,
    time_of_day: str,
    timezone_str: str,
    days_of_week: list[int] | None = None,
    day_of_month: int | None = None,
    interval_minutes: int | None = None,
    after: datetime | None = None,
) -> datetime | None:
    """Compute the next run datetime as a naive UTC datetime based on the schedule pattern."""
    import pytz

    tz = pytz.timezone(timezone_str) if timezone_str else pytz.UTC
    now = datetime.now(timezone.utc)

    if after:
        if after.tzinfo is None:
            after = after.replace(tzinfo=timezone.utc)
        base = after if after > now else now
    else:
        base = now

    if pattern == "every_minute":
        result = base + timedelta(minutes=1)
        return result.astimezone(pytz.UTC).replace(tzinfo=None)

    if pattern == "custom_interval":
        minutes = interval_minutes or 60
        result = base + timedelta(minutes=minutes)
        return result.astimezone(pytz.UTC).replace(tzinfo=None)

    hour, minute = 0, 0
    if time_of_day:
        parts = time_of_day.split(":")
        hour, minute = int(parts[0]), int(parts[1])

    if pattern == "hourly":
        candidate = base.astimezone(tz).replace(minute=minute, second=0, microsecond=0)
        if candidate <= base.astimezone(tz):
            candidate += timedelta(hours=1)
        return candidate.astimezone(pytz.UTC).replace(tzinfo=None)

    if pattern == "daily":
        candidate = base.astimezone(tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= base.astimezone(tz):
            candidate += timedelta(days=1)
        return candidate.astimezone(pytz.UTC).replace(tzinfo=None)

    if pattern == "weekly":
        target_days = sorted(days_of_week or [0])
        if not target_days:
            return None
        local_now = base.astimezone(tz)
        for offset in range(8):
            candidate_date = local_now.date() + timedelta(days=offset)
            if candidate_date.weekday() in target_days:
                candidate = tz.localize(
                    datetime.combine(candidate_date, datetime.min.time()).replace(
                        hour=hour, minute=minute, second=0
                    )
                )
                if candidate > local_now:
                    return candidate.astimezone(pytz.UTC).replace(tzinfo=None)
        return None

    if pattern == "monthly":
        dom = day_of_month or 1
        local_now = base.astimezone(tz)
        for month_offset in range(2):
            year = local_now.year + (local_now.month + month_offset - 1) // 12
            month = (local_now.month + month_offset - 1) % 12 + 1
            try:
                candidate = tz.localize(
                    datetime(year, month, dom, hour, minute, 0)
                )
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                candidate = tz.localize(
                    datetime(year, month, min(dom, last_day), hour, minute, 0)
                )
            if candidate > local_now:
                return candidate.astimezone(pytz.UTC).replace(tzinfo=None)
        return None

    return None


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
            "schedule_enabled": False,
            "schedule_pattern": None,
            "schedule_time": None,
            "schedule_days_of_week": None,
            "schedule_day_of_month": None,
            "schedule_interval_minutes": None,
            "schedule_timezone": "UTC",
            "schedule_next_run": None,
            "schedule_end_date": None,
            "schedule_last_triggered": None,
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
    def get_by_id(flow_id: str) -> dict | None:
        """Get a flow by ID without username check (for daemon use)."""
        doc = flows_collection.find_one({"id": flow_id})
        if doc is None:
            return None
        return doc

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

    @staticmethod
    def find_due_scheduled() -> list:
        """Find all flows that are due for scheduled execution."""
        now = datetime.utcnow()
        query = {
            "schedule_enabled": True,
            "schedule_next_run": {"$lte": now},
            "$or": [
                {"schedule_end_date": None},
                {"schedule_end_date": {"$gte": now}},
            ],
        }
        return list(flows_collection.find(query))

    @staticmethod
    def advance_schedule(flow_id: str, username: str) -> None:
        """After a scheduled run, compute and set the next run time."""
        doc = flows_collection.find_one({"id": flow_id, "username": username})
        if not doc or not doc.get("schedule_enabled"):
            return

        now = datetime.utcnow()
        next_run = compute_next_run(
            pattern=doc.get("schedule_pattern", "daily"),
            time_of_day=doc.get("schedule_time", "09:00"),
            timezone_str=doc.get("schedule_timezone", "UTC"),
            days_of_week=doc.get("schedule_days_of_week"),
            day_of_month=doc.get("schedule_day_of_month"),
            interval_minutes=doc.get("schedule_interval_minutes"),
            after=now,
        )

        end_date = doc.get("schedule_end_date")
        if end_date and next_run and next_run > end_date:
            flows_collection.update_one(
                {"id": flow_id, "username": username},
                {"$set": {
                    "schedule_enabled": False,
                    "schedule_next_run": None,
                    "schedule_last_triggered": now,
                    "updated_at": now,
                }},
            )
            return

        flows_collection.update_one(
            {"id": flow_id, "username": username},
            {"$set": {
                "schedule_next_run": next_run,
                "schedule_last_triggered": now,
                "updated_at": now,
            }},
        )
