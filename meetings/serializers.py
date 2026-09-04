from datetime import datetime, timezone as dt_timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils import timezone
from users.serializers import UserSummarySerializer
from .models import Meeting
from .services import schedule_meeting

User = get_user_model()


def parse_local(value, timezone_name, field_name):
    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise serializers.ValidationError({"input_timezone": "Use a valid IANA timezone."}) from exc
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({field_name: "Use ISO 8601 format, e.g. 2026-09-10T14:30:00."}) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_tz)
    return parsed.astimezone(dt_timezone.utc)


class MeetingSerializer(serializers.ModelSerializer):
    organizer = UserSummarySerializer(read_only=True)
    invitee = UserSummarySerializer(read_only=True)

    starts_at_local = serializers.SerializerMethodField()
    ends_at_local = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    can_join_video = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = (
            "id",
            "title",
            "description",
            "organizer",
            "invitee",
            "starts_at",
            "ends_at",
            "starts_at_local",
            "ends_at_local",
            "status",
            "can_join_video",
            "created_at",
        )

    def get_status(self, obj):
        if obj.status == Meeting.Status.CANCELLED:
            return "cancelled"

        if obj.ends_at <= timezone.now():
            return "completed"

        return "scheduled"

    def _localize(self, value):
        tz = ZoneInfo(
            self.context["request"].user.preferred_timezone
        )
        return value.astimezone(tz).isoformat()

    def get_starts_at_local(self, obj):
        return self._localize(obj.starts_at)

    def get_ends_at_local(self, obj):
        return self._localize(obj.ends_at)

    def get_can_join_video(self, meeting):
        if meeting.status == Meeting.Status.CANCELLED:
            return False

        current_time = timezone.now()

        if current_time >= meeting.ends_at:
            return False

        join_window_opens = meeting.starts_at - timedelta(
            minutes=settings.VIDEO_JOIN_EARLY_MINUTES
        )

        return current_time >= join_window_opens

class MeetingCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    invitee_id = serializers.PrimaryKeyRelatedField(source="invitee", queryset=User.objects.all())
    start_time_local = serializers.CharField()
    end_time_local = serializers.CharField()
    input_timezone = serializers.CharField(required=False)

    def validate(self, attrs):
        timezone_name = attrs.get("input_timezone") or self.context["request"].user.preferred_timezone
        attrs["starts_at"] = parse_local(attrs.pop("start_time_local"), timezone_name, "start_time_local")
        attrs["ends_at"] = parse_local(attrs.pop("end_time_local"), timezone_name, "end_time_local")
        attrs.pop("input_timezone", None)
        return attrs

    def create(self, validated_data):
        return schedule_meeting(organizer=self.context["request"].user, **validated_data)

    def to_representation(self, instance):
        return MeetingSerializer(instance, context=self.context).data

