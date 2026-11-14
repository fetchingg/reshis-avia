from django.conf import settings
from django.db import models


class Calculation(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calculations")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    result = models.JSONField()

    class Meta:
        ordering = ["-created_at", "-pk"]
