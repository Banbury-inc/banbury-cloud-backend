import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import MapPlace


def _get_username(request):
    return getattr(request, 'username_from_token', None)


@csrf_exempt
def places_list(request):
    """GET /maps/places/  – list saved places (recents + favorites)
       POST /maps/places/ – save / bump a visited place
    """
    username = _get_username(request)
    if not username:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "GET":
        places = MapPlace.list_for_user(username)
        return JsonResponse({"places": places})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = {}

        longitude = body.get("longitude")
        latitude = body.get("latitude")
        if longitude is None or latitude is None:
            return JsonResponse({"error": "longitude and latitude are required"}, status=400)

        try:
            place = MapPlace.upsert_recent(
                username=username,
                name=body.get("name", "Untitled place"),
                longitude=float(longitude),
                latitude=float(latitude),
                zoom=float(body.get("zoom", 9)),
            )
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid coordinate values"}, status=400)
        return JsonResponse(place, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def place_detail(request, place_id: str):
    """PUT /maps/places/{id}/    – toggle favorite / rename
       DELETE /maps/places/{id}/ – delete a saved place
    """
    username = _get_username(request)
    if not username:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method in ("PUT", "PATCH"):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = {}

        updates: dict = {}
        if "name" in body:
            updates["name"] = body["name"]
        if "is_favorite" in body:
            updates["is_favorite"] = bool(body["is_favorite"])

        if not updates:
            return JsonResponse({"error": "Nothing to update"}, status=400)

        place = MapPlace.update(place_id, username, updates)
        if place is None:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse(place)

    if request.method == "DELETE":
        deleted = MapPlace.delete(place_id, username)
        if not deleted:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse({"success": True, "message": "Place deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)
