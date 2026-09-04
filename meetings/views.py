from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from rest_framework import decorators, mixins, response, status, viewsets
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.conf import settings
from .livekit import create_video_token
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)
from .models import Meeting
from .serializers import MeetingCreateSerializer, MeetingSerializer
from .services import cancel_meeting


class MeetingViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    def get_queryset(self):
        qs = Meeting.objects.filter(Q(organizer=self.request.user) | Q(invitee=self.request.user)).select_related("organizer", "invitee").order_by("-starts_at")
        period = self.request.query_params.get("period")
        if period == "upcoming":
            qs = qs.filter(ends_at__gte=timezone.now(), status=Meeting.Status.SCHEDULED)
        elif period == "past":
            qs = qs.filter(ends_at__lt=timezone.now())
        return qs

    def get_serializer_class(self):
        return MeetingCreateSerializer if self.action == "create" else MeetingSerializer

    @decorators.action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        meeting = self.get_object()
        if meeting.organizer_id != request.user.id:
            raise PermissionDenied("Only the organizer can cancel this meeting.")
        if meeting.status == Meeting.Status.CANCELLED:
            return response.Response(MeetingSerializer(meeting, context={"request": request}).data)
        cancel_meeting(meeting=meeting)
        return response.Response(MeetingSerializer(meeting, context={"request": request}).data, status=status.HTTP_200_OK)

    @decorators.action(detail=True,methods=("post",),url_path="video-token")
    def video_token(self, request, pk=None):
        meeting = self.get_object()
        current_time = timezone.now()

        if meeting.status == Meeting.Status.CANCELLED:
            raise ValidationError({
                "meeting": "A cancelled meeting cannot be joined."
            })

        if current_time >= meeting.ends_at:
            raise ValidationError({
                "meeting": "This meeting has already ended."
            })

        join_window_opens = meeting.starts_at - timedelta(
            minutes=settings.VIDEO_JOIN_EARLY_MINUTES
        )

        if current_time < join_window_opens:
            raise ValidationError({
                "meeting": (
                    "The video call can be joined "
                    f"{settings.VIDEO_JOIN_EARLY_MINUTES} minutes "
                    "before its start time."
                )
            })

        credentials = create_video_token(
            meeting=meeting,
            user=request.user,
        )

        return response.Response(
            credentials,
            status=status.HTTP_200_OK,
        )
class MeetingRoomView(LoginRequiredMixin, TemplateView):
    template_name = "meetings/video_room.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        meeting = get_object_or_404(
            Meeting.objects.select_related(
                "organizer",
                "invitee",
            ).filter(
                Q(organizer=self.request.user)
                | Q(invitee=self.request.user)
            ),
            pk=self.kwargs["pk"],
        )

        context["meeting"] = meeting
        return context