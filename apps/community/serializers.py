from rest_framework import serializers

from .models import CommunityComment, CommunityPost, LostItem, Story, StoryComment


class StorySerializer(serializers.ModelSerializer):
    """Serializer for the Story model, including fields for user information, media URLs, and interaction status such as likes and views."""

    username = serializers.ReadOnlyField(source="user.username")
    user_avatar = serializers.SerializerMethodField()
    is_viewed = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    likes = serializers.IntegerField(source="total_likes", read_only=True)
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "username",
            "user_avatar",
            "image",
            "video",
            "caption",
            "created_at",
            "is_viewed",
            "is_liked",
            "likes",
            "comment_count",
        ]
        read_only_fields = ["user", "created_at", "likes"]

    def to_representation(self, instance):
        """Override the default to_representation method to include absolute URLs for media fields and handle potential errors when fetching URLs."""
        data = super().to_representation(instance)
        if instance.image:
            try:
                data["image"] = instance.image.url
            except Exception as e:
                print(f"Error occurred while fetching image URL: {e}")
                data["image"] = None
        if instance.video:
            try:
                data["video"] = instance.video.url
            except Exception as e:
                print(f"Error occurred while fetching video URL: {e}")
                data["video"] = None
        return data

    def get_user_avatar(self, obj):
        """
        Get the absolute URL of the user's avatar if it exists, otherwise return None.
        This method checks if the user has an avatar and builds the absolute URL using the request context.
        """
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None

    def get_is_viewed(self, obj):
        """Check if the current user has viewed the story by checking the viewed_by ManyToMany relationship."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.viewed_by.filter(id=request.user.id).exists()
        return False

    def get_is_liked(self, obj):
        """Check if the current user has liked the story by checking the liked_by ManyToMany relationship."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.liked_by.filter(id=request.user.id).exists()
        return False


class StoryViewerSerializer(serializers.ModelSerializer):
    """Serializer for representing users who have viewed a story, including their username and avatar."""

    from apps.users.models import User

    class Meta:
        from apps.users.models import User

        model = User
        fields = ["id", "username", "avatar"]


class StoryCommentSerializer(serializers.ModelSerializer):
    """Serializer for the StoryComment model, including fields for the comment text, related story, user information, and ownership status."""

    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = StoryComment
        fields = ["id", "story", "username", "avatar", "text", "created_at", "is_owner"]
        read_only_fields = ["user", "created_at"]

    def get_is_owner(self, obj):
        """Check if the current user is the owner of the comment by comparing the comment's user with the request user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False

    def get_avatar(self, obj):
        """
        Get the absolute URL of the user's avatar if it exists, otherwise return None.
        This method checks if the user has an avatar and builds the absolute URL using the request context.
        """
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class CommunityCommentSerializer(serializers.ModelSerializer):
    """Serializer for the CommunityComment model, including fields for the comment text, related post, user information, and ownership status."""

    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = CommunityComment
        fields = ["id", "post", "username", "avatar", "text", "created_at", "is_owner"]
        read_only_fields = ["user", "created_at"]

    def get_is_owner(self, obj):
        """Check if the current user is the owner of the comment by comparing the comment's user with the request user."""
        return obj.user == self.context["request"].user

    def get_avatar(self, obj):
        """Get the absolute URL of the user's avatar if it exists, otherwise return None."""
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class CommunityPostSerializer(serializers.ModelSerializer):
    """Serializer for the CommunityPost model, including fields for the post content, category, anonymity option, user information, interaction status such as likes and comments, and ownership status."""

    username = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)
    likes = serializers.IntegerField(source="total_likes", read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            "id",
            "username",
            "avatar",
            "content",
            "image",
            "category",
            "is_anonymous",
            "created_at",
            "likes",
            "comment_count",
            "is_liked",
            "is_owner",
        ]
        read_only_fields = ["user", "created_at", "likes"]

    def get_is_liked(self, obj):
        """Check if the current user has liked the post by checking the liked_by ManyToMany relationship."""
        user = self.context["request"].user
        if user.is_authenticated:
            return obj.liked_by.filter(id=user.id).exists()
        return False

    def get_is_owner(self, obj):
        """Check if the current user is the owner of the post by comparing the post's user with the request user."""
        return obj.user == self.context["request"].user

    def get_username(self, obj):
        """Return the username of the post's author, or "Anonymous Student" if the post is marked as anonymous. This method checks the is_anonymous field of the post and returns the appropriate username based on that."""
        return "Anonymous Student" if obj.is_anonymous else obj.user.username

    def get_avatar(self, obj):
        """Get the absolute URL of the user's avatar if it exists and the post is not anonymous, otherwise return None. This method checks if the post is marked as anonymous and if the user has an avatar, then builds the absolute URL using the request context."""
        if obj.is_anonymous:
            return None
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class LostItemSerializer(serializers.ModelSerializer):
    """Serializer for the LostItem model, including fields for item details, user information, and ownership status. This serializer also includes methods to determine if the current user is the owner of the lost item report and to provide absolute URLs for user avatars if they exist."""

    is_owner = serializers.SerializerMethodField()
    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.ImageField(source="user.avatar", read_only=True)

    class Meta:
        model = LostItem
        fields = "__all__"
        read_only_fields = ["user", "created_at", "is_resolved"]

    def get_is_owner(self, obj):
        """Check if the current user is the owner of the lost item report by comparing the report's user with the request user. This method retrieves the request from the serializer context and checks if the user is authenticated before performing the comparison."""
        request = self.context.get("request")
        if request and request.user:
            return obj.user == request.user
        return False
