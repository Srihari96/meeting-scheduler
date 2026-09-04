from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from psycopg.types.range import Range
from rest_framework.exceptions import ValidationError

from .models import BusySlot, Meeting


@transaction.atomic
def schedule_meeting(*, organizer, invitee, title, description, starts_at, ends_at):
    if organizer.pk == invitee.pk:
        raise ValidationError({"invitee_id": "A one-on-one meeting needs another user."})
    if ends_at <= starts_at:
        raise ValidationError({"end_time_local": "End time must be after start time."})
    if starts_at <= timezone.now():
        raise ValidationError({"start_time_local": "Meeting must start in the future."})

    earliest = timezone.now() + timedelta(minutes=invitee.minimum_notice_minutes)
    if starts_at < earliest:
        raise ValidationError({
            "start_time_local": f"{invitee.username} requires at least {invitee.minimum_notice_minutes} minutes notice."
        })

    meeting = Meeting.objects.create(
        organizer=organizer, invitee=invitee, title=title, description=description,
        starts_at=starts_at, ends_at=ends_at,
    )
    interval = Range(starts_at, ends_at, "[)")  # Adjacent meetings are allowed.
    try:
        BusySlot.objects.bulk_create([
            BusySlot(meeting=meeting, user=organizer, time_range=interval),
            BusySlot(meeting=meeting, user=invitee, time_range=interval),
        ])
    except IntegrityError as exc:
        raise ValidationError({"non_field_errors": ["One of the users already has an overlapping meeting."]}) from exc
    return meeting


@transaction.atomic
def cancel_meeting(*, meeting):
    meeting.status = Meeting.Status.CANCELLED
    meeting.save(update_fields=("status", "updated_at"))
    meeting.busy_slots.update(active=False)
    return meeting
