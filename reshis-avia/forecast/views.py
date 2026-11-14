
import logging
from functools import lru_cache

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from config.http import error, read_json
from .models import Calculation
from .services import ForecastError, load_data

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_catalog():
    return load_data(settings.FORECAST_CSV_PATH, settings.ROUTES_CSV_PATH)


@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, "forecast/index.html")


@require_GET
def meta_api(request):
    try:
        return JsonResponse(get_catalog().get_meta())
    except (OSError, ValueError):
        logger.exception("Не удалось загрузить CSV")
        return error("Не удалось загрузить расписание. Проверьте файлы CSV на сервере", 503, "data_unavailable")


@require_POST
def forecast_api(request):
    try:
        data = read_json(request)
    except ValueError as exc:
        return error(str(exc))
    try:
        catalog = get_catalog()
    except (OSError, ValueError):
        logger.exception("Не удалось загрузить CSV")
        return error("Данные прогноза временно недоступны", 503, "data_unavailable")
    try:
        result = catalog.compute_forecast(data.get("origin"), data.get("destination"), data.get("date"), data.get("price"))
    except ForecastError as exc:
        return error(str(exc), exc.status, exc.code, {exc.field: [str(exc)]} if exc.field else None)
    if request.user.is_authenticated:
        Calculation.objects.create(user=request.user, result=result)
    return JsonResponse(result)


@login_required
@require_GET
def history(request):
    page = Paginator(Calculation.objects.filter(user=request.user), 20).get_page(request.GET.get("page"))
    return render(request, "forecast/history.html", {"page": page})


@login_required
@require_POST
def clear_history(request):
    Calculation.objects.filter(user=request.user).delete()
    return redirect("history")
