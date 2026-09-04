from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    preferred_timezone = models.CharField(max_length=64, default="UTC")
    minimum_notice_minutes = models.PositiveIntegerField(default=30)

    def clean(self):
        super().clean()
        try:
            ZoneInfo(self.preferred_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValidationError({"preferred_timezone": "Use a valid IANA timezone, e.g. Asia/Kolkata."}) from exc

