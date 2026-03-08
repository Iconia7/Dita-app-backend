from rest_framework import serializers

from .models import Announcement, Event


class EventSerializer(serializers.ModelSerializer):
    """Serializer for the Event model, including a field to indicate if the current user has RSVPed to the event."""

    has_rsvped = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["id", "title", "description", "date", "venue", "image", "has_rsvped"]

    def get_has_rsvped(self, obj):
        """Check if the current user has RSVPed to the event."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.rsvp_set.filter(user=request.user).exists()
        return False


class AnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for the Announcement model, including all fields."""

    class Meta:
        model = Announcement
        fields = "__all__"
