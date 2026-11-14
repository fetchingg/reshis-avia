from django.apps import AppConfig


class ForecastConfig(AppConfig):
    #подкл калькулятор и историю
    default_auto_field = "django.db.models.BigAutoField"
    name = "forecast"
