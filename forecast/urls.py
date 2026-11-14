from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="calculator"),
    path("api/meta/", views.meta_api),
    path("api/forecast/", views.forecast_api),
    path("history/", views.history, name="history"),
    path("history/clear/", views.clear_history, name="clear_history"),
]
