
from django.urls import include, path

urlpatterns = [path("", include("forecast.urls")), path("", include("accounts.urls"))]
