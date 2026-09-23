from rest_framework import serializers

from .models import Announcement, Event, HackFestRegistration


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


class MemberRosterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=25, required=False, allow_blank=True)
    institution = serializers.CharField(max_length=150, required=False, allow_blank=True)
    student_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    role = serializers.CharField(max_length=80, required=False, allow_blank=True)


class HackFestRegistrationSerializer(serializers.ModelSerializer):
    members = MemberRosterSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = HackFestRegistration
        fields = [
            "id",
            "event_slug",
            "registration_type",
            "team_name",
            "team_size",
            "full_name",
            "email",
            "phone",
            "institution",
            "is_daystar",
            "student_id",
            "campus",
            "track_preference",
            "role_preference",
            "roster_data",
            "members",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        reg_type = attrs.get("registration_type", "team")
        team_name = attrs.get("team_name")
        members = attrs.get("members", [])
        event_slug = attrs.get("event_slug", "hack-fest-26")
        email = attrs.get("email")

        # Check unique email for this event
        if HackFestRegistration.objects.filter(event_slug=event_slug, email=email).exists():
            raise serializers.ValidationError({"email": "This email is already registered for Hack Fest '26."})

        # Normalize student ID for Daystar students (e.g., 23-1670 or 231670)
        is_daystar = attrs.get("is_daystar", False)
        student_id = (attrs.get("student_id") or "").strip()
        if is_daystar and student_id:
            import re
            if re.match(r"^\d{6}$", student_id):
                student_id = f"{student_id[:2]}-{student_id[2:]}"
            attrs["student_id"] = student_id

        if reg_type == "team":
            if not team_name or not team_name.strip():
                raise serializers.ValidationError({"team_name": "Team name is required for team registrations."})
            
            team_size = 1 + len(members)
            if team_size < 2 or team_size > 5:
                raise serializers.ValidationError({"team_size": "Teams must have between 2 and 5 builders total (1 lead + 1 to 4 teammates)."})
            attrs["team_size"] = team_size
            attrs["roster_data"] = members
        else:
            attrs["team_size"] = 1
            attrs["roster_data"] = []

        return attrs

    def create(self, validated_data):
        validated_data.pop("members", None)
        return super().create(validated_data)
