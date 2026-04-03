from rest_framework import serializers

from .models import GroupMessage, StudyGroup


class GroupMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the GroupMessage model, including fields for the message content, timestamp, and user information such as username and avatar.
    The username is read-only and derived from the related user model, while the avatar is obtained through a method that checks if the user has an avatar image.
    """

    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = GroupMessage
        fields = ["id", "username", "avatar", "content", "timestamp"]

    def get_avatar(self, obj):
        """
        Get the URL of the user's avatar image if it exists, otherwise return None.
        This method checks if the user associated with the message has an avatar and returns its URL for use in the serialized data.
        """
        if obj.user.avatar:
            return obj.user.avatar.url
        return None


class StudyGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for the StudyGroup model, including fields for group details such as name, course code, description, member count, and membership status for the current user.
    The member count is calculated using the count of related members, and the is_member field indicates whether the current user is a member of the study group, allowing for dynamic representation of group membership in the API responses.
    """

    member_count = serializers.IntegerField(source="members.count", read_only=True)
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = StudyGroup
        fields = ["id", "name", "course_code", "description", "member_count", "is_member", "created_at", "creator"]
        read_only_fields = ["creator"]

    def get_is_member(self, obj):
        """Check if the current user is a member of the study group."""
        user = self.context.get("request").user
        if user.is_authenticated:
            return obj.members.filter(id=user.id).exists()
        return False
