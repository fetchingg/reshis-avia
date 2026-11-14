from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_page, name="register"),
    path("login/", views.login_page, name="login"),
    path("api/auth/register/", views.register_api),
    path("api/auth/login/", views.login_api),
    path("api/auth/logout/", views.logout_api),
    path("api/auth/me/", views.me_api),
]
