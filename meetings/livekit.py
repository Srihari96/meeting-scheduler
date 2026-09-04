from datetime import timedelta

from django.conf import settings
from livekit import api


def create_video_token(*, meeting, user):
    participant_name = (
        user.get_full_name().strip()
        or user.username
    )

    token = (
        api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
        )
        .with_identity(f"user-{user.pk}")
        .with_name(participant_name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=str(meeting.video_room_id),
                can_publish=True,
                can_subscribe=True,
            )
        )
        .with_ttl(timedelta(minutes=15))
        .to_jwt()
    )

    return {
        "server_url": settings.LIVEKIT_URL,
        "participant_token": token,
        "room_name": str(meeting.video_room_id),
    }