from rest_framework import serializers
from .models import User
from .timezones import TIMEZONE_CHOICES


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "preferred_timezone", "minimum_notice_minutes")


class RegisterSerializer(UserSummarySerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    preferred_timezone = serializers.ChoiceField(choices=TIMEZONE_CHOICES, default="UTC")

    class Meta(UserSummarySerializer.Meta):
        fields = UserSummarySerializer.Meta.fields + ("email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class PreferenceSerializer(serializers.ModelSerializer):
    preferred_timezone = serializers.ChoiceField(choices=TIMEZONE_CHOICES)

    class Meta:
        model = User
        fields = ("preferred_timezone", "minimum_notice_minutes")
