
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from config.http import error, read_json
from .forms import RegistrationForm
from .models import LoginThrottle, User


def user_data(user):
    return {"email": user.email, "name": user.name}


@ensure_csrf_cookie
@require_GET
def register_page(request):
    return redirect("history") if request.user.is_authenticated else render(request, "accounts/register.html")


@ensure_csrf_cookie
@require_GET
def login_page(request):
    return redirect("history") if request.user.is_authenticated else render(request, "accounts/login.html")


@require_POST
def register_api(request):
    try:
        data = read_json(request)
    except ValueError as exc:
        return error(str(exc))
    if any(not isinstance(data.get(k), str) for k in ("name", "email", "password", "password2")):
        return error("Заполните имя, email и оба пароля")
    form = RegistrationForm(data)
    if not form.is_valid():
        return error("Проверьте поля регистрации", fields=dict(form.errors))
    cleaned = form.cleaned_data
    if User.objects.filter(email=cleaned["email"]).exists():
        return error("Такой email уже зарегистрирован", 409, "email_exists", {"email": ["Этот email уже используется"]})
    try:
        with transaction.atomic():
            user = User.objects.create_user(cleaned["email"], cleaned["password"], name=cleaned["name"])
    except IntegrityError:
        return error("Такой email уже зарегистрирован", 409, "email_exists")
    login(request, user)
    request.session.set_expiry(0)
    return JsonResponse({"user": user_data(user)}, status=201)


@require_POST
def login_api(request):
    try:
        data = read_json(request)
    except ValueError as exc:
        return error(str(exc))
    email, password = data.get("email"), data.get("password")
    remember = data.get("remember", False)
    if not isinstance(email, str) or not isinstance(password, str) or not isinstance(remember, bool):
        return error("Укажите email и пароль")
    email = email.strip().casefold()
    if not email or len(email) > 254 or not password or len(password) > 128:
        return error("Укажите корректные email и пароль")
    key = salted_hmac("login-throttle", email + "|" + request.META.get("REMOTE_ADDR", ""), algorithm="sha256").hexdigest()
    now = timezone.now()
    # пять минут считаются от последней ошибкт
    with transaction.atomic():
        attempt, _ = LoginThrottle.objects.get_or_create(key=key, defaults={"updated_at": now})
        if attempt.updated_at <= now - timedelta(minutes=5):
            attempt.failures = 0
        if attempt.failures >= 5:
            response = error("Слишком много попыток, попробуйте позже", 429, "rate_limited")
            response["Retry-After"] = max(1, int((attempt.updated_at + timedelta(minutes=5) - now).total_seconds()))
            return response
        user = authenticate(request, email=email, password=password)
        if user is None:
            attempt.failures += 1
            attempt.updated_at = now
            attempt.save(update_fields=["failures", "updated_at"])
            return error("Неверный email или пароль", code="invalid_credentials")
        attempt.delete()
    login(request, user)
    request.session.set_expiry(14 * 24 * 60 * 60 if remember else 0)
    return JsonResponse({"user": user_data(user)})


@require_POST
def logout_api(request):
    if not request.user.is_authenticated:
        return error("Сначала войдите в аккаунт", 401, "authentication_required")
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def me_api(request):
    return JsonResponse({"user": user_data(request.user) if request.user.is_authenticated else None})
