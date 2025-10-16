"""
Simple serializers for MongoDB data validation
"""
from rest_framework import serializers


class MeetingJoinRequestSerializer(serializers.Serializer):
    meetingUrl = serializers.URLField()
    platform = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    settings = serializers.DictField(required=False, default=dict)
    scheduledStartTime = serializers.DateTimeField(required=False)


class MeetingConfigUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    default_settings = serializers.DictField(required=False)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    notification_settings = serializers.DictField(required=False)


class BotSettingsSerializer(serializers.Serializer):
    profilePictureUrl = serializers.URLField(required=False, allow_blank=True)
    botName = serializers.CharField(max_length=100, required=False, allow_blank=True)