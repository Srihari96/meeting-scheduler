import uuid
from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import Q


class Meeting(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organized_meetings")
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invited_meetings")
    starts_at = models.DateTimeField(help_text="Stored in UTC")
    ends_at = models.DateTimeField(help_text="Stored in UTC")
    video_room_id = models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("starts_at",)
        indexes = [models.Index(fields=("starts_at", "ends_at"))]


class BusySlot(models.Model):
    """One row per meeting participant; the DB constraint prevents races."""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="busy_slots")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="busy_slots")
    time_range = DateTimeRangeField()
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("meeting", "user"), name="one_slot_per_meeting_user"),
            ExclusionConstraint(
                name="prevent_overlapping_active_user_meetings",
                expressions=(("user", RangeOperators.EQUAL), ("time_range", RangeOperators.OVERLAPS)),
                condition=Q(active=True),
            ),
        ]

