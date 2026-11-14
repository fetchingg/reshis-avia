
import json

from django.http import JsonResponse
from django.shortcuts import render


def error(message, status=400, code="validation_error", fields=None):
    detail = {"code": code, "message": message}
    if fields:
        detail["fields"] = fields
    return JsonResponse({"error": detail}, status=status)


def read_json(request):
    if request.content_type != "application/json" or len(request.body) > 16384:
        raise ValueError("Ожидается JSON-объект размером до 16 КБ")
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Не удалось прочитать JSON-запрос") from exc
    if not isinstance(data, dict):
        raise ValueError("Ожидается JSON-объект")
    return data


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return error("Сессия страницы устарела. Обновите страницу и повторите", 403, "csrf_error")
    return render(request, "403.html", status=403)
