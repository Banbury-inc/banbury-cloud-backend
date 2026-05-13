import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Skill


def _get_username(request):
    return getattr(request, "username_from_token", None)


def _read_body(request) -> dict:
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


@csrf_exempt
def skills_list(request):
    username = _get_username(request)
    if not username:
        return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)

    if request.method == "GET":
        return JsonResponse({"success": True, "skills": Skill.list_for_user(username)})

    if request.method == "POST":
        body = _read_body(request)
        content = body.get("content", "")
        if not isinstance(content, str) or not content.strip():
            return JsonResponse({"success": False, "error": "Skill content is required"}, status=400)

        skill = Skill.create(
            username=username,
            content=content,
            enabled=body.get("enabled", True),
        )
        return JsonResponse({"success": True, "skill": skill}, status=201)

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@csrf_exempt
def skill_detail(request, skill_id: str):
    username = _get_username(request)
    if not username:
        return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)

    if request.method == "GET":
        skill = Skill.get(skill_id, username)
        if skill is None:
            return JsonResponse({"success": False, "error": "Not found"}, status=404)
        return JsonResponse({"success": True, "skill": skill})

    if request.method in ("PUT", "PATCH"):
        body = _read_body(request)
        skill = Skill.update(skill_id, username, body)
        if skill is None:
            return JsonResponse({"success": False, "error": "Not found"}, status=404)
        return JsonResponse({"success": True, "skill": skill})

    if request.method == "DELETE":
        deleted = Skill.delete(skill_id, username)
        if not deleted:
            return JsonResponse({"success": False, "error": "Not found"}, status=404)
        return JsonResponse({"success": True, "message": "Skill deleted"})

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
