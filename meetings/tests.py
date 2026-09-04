from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status

from .models import Meeting

User = get_user_model()


class MeetingApiTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="password123", preferred_timezone="Asia/Kolkata", minimum_notice_minutes=30)
        self.bob = User.objects.create_user(username="bob", password="password123", minimum_notice_minutes=30)
        self.client = APIClient()
        self.client.force_authenticate(self.alice)

    def payload(self, start, end):
        return {"title": "Planning", "invitee_id": self.bob.id, "start_time_local": start.isoformat(), "end_time_local": end.isoformat(), "input_timezone": "UTC"}

    def test_create_and_localized_output(self):
        start = timezone.now() + timedelta(hours=2)
        result = self.client.post("/api/meetings/", self.payload(start, start + timedelta(minutes=30)), format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertIn("+05:30", result.data["starts_at_local"])

    def test_overlap_is_rejected(self):
        start = timezone.now() + timedelta(hours=2)
        self.client.post("/api/meetings/", self.payload(start, start + timedelta(hours=1)), format="json")
        result = self.client.post("/api/meetings/", self.payload(start + timedelta(minutes=15), start + timedelta(hours=2)), format="json")
        self.assertEqual(result.status_code, 400)
        self.assertEqual(Meeting.objects.count(), 1)

    def test_minimum_notice_is_enforced(self):
        start = timezone.now() + timedelta(minutes=10)
        result = self.client.post("/api/meetings/", self.payload(start, start + timedelta(minutes=30)), format="json")
        self.assertEqual(result.status_code, 400)
    
    def test_notice_period_only_applies_to_invitee(self):
        self.alice.minimum_notice_minutes = 180
        self.alice.save(
            update_fields=["minimum_notice_minutes"]
        )

        self.bob.minimum_notice_minutes = 10
        self.bob.save(
            update_fields=["minimum_notice_minutes"]
        )

        start = timezone.now() + timedelta(minutes=30)

        result = self.client.post(
            "/api/meetings/",
            self.payload(
                start,
                start + timedelta(minutes=30),
            ),
            format="json",
        )

        self.assertEqual(
            result.status_code,
            status.HTTP_201_CREATED,
            result.data,
        )

class VideoTokenApiTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizer",
            password="password123",
            preferred_timezone="Asia/Kolkata",
            minimum_notice_minutes=30,
        )

        self.invitee = User.objects.create_user(
            username="invitee",
            password="password123",
            preferred_timezone="UTC",
            minimum_notice_minutes=30,
        )

        self.outsider = User.objects.create_user(
            username="outsider",
            password="password123",
        )

        self.client = APIClient()
        self.client.force_authenticate(
            self.organizer
        )

    def create_meeting(
        self,
        *,
        starts_at=None,
        ends_at=None,
        status=Meeting.Status.SCHEDULED,
    ):
        starts_at = (
            starts_at
            or timezone.now() + timedelta(minutes=5)
        )

        ends_at = (
            ends_at
            or starts_at + timedelta(minutes=30)
        )

        return Meeting.objects.create(
            title="Video discussion",
            description="Test video meeting",
            organizer=self.organizer,
            invitee=self.invitee,
            starts_at=starts_at,
            ends_at=ends_at,
            status=status,
        )

    @override_settings(
        VIDEO_JOIN_EARLY_MINUTES=10
    )
    @patch("meetings.views.create_video_token")
    def test_participant_can_get_video_token(
        self,
        mocked_create_token,
    ):
        mocked_create_token.return_value = {
            "server_url": "ws://127.0.0.1:7880",
            "participant_token": "test-token",
            "room_name": "test-room",
        }

        meeting = self.create_meeting()

        response = self.client.post(
            f"/api/meetings/{meeting.id}/video-token/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["participant_token"],
            "test-token",
        )

        mocked_create_token.assert_called_once_with(
            meeting=meeting,
            user=self.organizer,
        )

    @override_settings(
        VIDEO_JOIN_EARLY_MINUTES=10
    )
    @patch("meetings.views.create_video_token")
    def test_invitee_can_get_video_token(
        self,
        mocked_create_token,
    ):
        mocked_create_token.return_value = {
            "server_url": "ws://127.0.0.1:7880",
            "participant_token": "invitee-token",
            "room_name": "test-room",
        }

        meeting = self.create_meeting()

        self.client.force_authenticate(
            self.invitee
        )

        response = self.client.post(
            f"/api/meetings/{meeting.id}/video-token/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    @override_settings(
        VIDEO_JOIN_EARLY_MINUTES=10
    )
    def test_outsider_cannot_get_video_token(self):
        meeting = self.create_meeting()

        self.client.force_authenticate(
            self.outsider
        )

        response = self.client.post(
            f"/api/meetings/{meeting.id}/video-token/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    @override_settings(
        VIDEO_JOIN_EARLY_MINUTES=10
    )
    def test_cancelled_meeting_cannot_be_joined(self):
        meeting = self.create_meeting(
            status=Meeting.Status.CANCELLED,
        )

        response = self.client.post(
            f"/api/meetings/{meeting.id}/video-token/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "cancelled",
            str(response.data).lower(),
        )

    @override_settings(
        VIDEO_JOIN_EARLY_MINUTES=10
    )
    def test_completed_meeting_cannot_be_joined(self):
        starts_at = (
            timezone.now() - timedelta(hours=1)
        )

        meeting = self.create_meeting(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
        )

        response = self.client.post(
            f"/api/meetings/{meeting.id}/video-token/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "ended",
            str(response.data).lower(),
        )

    @override_settings(
        VIDEO_JOIN_EARLY_MINUTES=10
    )
    def test_meeting_cannot_be_joined_too_early(self):
        starts_at = (
            timezone.now() + timedelta(minutes=30)
        )

        meeting = self.create_meeting(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
        )

        response = self.client.post(
            f"/api/meetings/{meeting.id}/video-token/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "10 minutes",
            str(response.data),
        )

class MeetingStatusApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            password="password123",
            preferred_timezone="Asia/Kolkata",
        )

        self.other_user = User.objects.create_user(
            username="bob",
            password="password123",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_meeting(
        self,
        *,
        title,
        starts_at,
        ends_at,
        meeting_status=Meeting.Status.SCHEDULED,
    ):
        return Meeting.objects.create(
            title=title,
            organizer=self.user,
            invitee=self.other_user,
            starts_at=starts_at,
            ends_at=ends_at,
            status=meeting_status,
        )

    def test_past_scheduled_meeting_is_completed(self):
        start = timezone.now() - timedelta(hours=1)

        meeting = self.create_meeting(
            title="Past meeting",
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
        )

        response = self.client.get(
            f"/api/meetings/{meeting.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "completed",
        )

        # The stored status remains scheduled.
        meeting.refresh_from_db()

        self.assertEqual(
            meeting.status,
            Meeting.Status.SCHEDULED,
        )

    def test_cancelled_status_takes_precedence(self):
        start = timezone.now() - timedelta(hours=1)

        meeting = self.create_meeting(
            title="Cancelled meeting",
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
            meeting_status=Meeting.Status.CANCELLED,
        )

        response = self.client.get(
            f"/api/meetings/{meeting.id}/"
        )

        self.assertEqual(
            response.data["status"],
            "cancelled",
        )

    def test_meetings_are_ordered_latest_first(self):
        current_time = timezone.now()

        older = self.create_meeting(
            title="Older",
            starts_at=current_time + timedelta(hours=1),
            ends_at=current_time + timedelta(hours=2),
        )

        newer = self.create_meeting(
            title="Newer",
            starts_at=current_time + timedelta(hours=3),
            ends_at=current_time + timedelta(hours=4),
        )

        response = self.client.get(
            "/api/meetings/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        meetings = response.data["results"]

        self.assertEqual(
            meetings[0]["id"],
            newer.id,
        )

        self.assertEqual(
            meetings[1]["id"],
            older.id,
        )