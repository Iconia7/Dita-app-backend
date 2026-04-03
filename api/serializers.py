from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Achievement,
    Announcement,
    AppConfig,
    AppUpdate,
    CommunityComment,
    CommunityPost,
    Event,
    Exam,
    GroupMessage,
    LostItem,
    Payment,
    Promotion,
    Resource,
    Story,
    StoryComment,
    StudyGroup,
    Task,
    User,
    UserAchievement,
)


class StorySerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    user_avatar = serializers.SerializerMethodField()
    is_viewed = serializers.SerializerMethodField()

    # Use ImageField for uploads, but override to_representation for URL output
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
        """Override to return full URLs for image/video"""
        data = super().to_representation(instance)

        # Convert image to full URL
        if instance.image:
            try:
                data["image"] = instance.image.url
            except Exception as e:
                print(f"Error occurred while fetching image URL: {e}")
                data["image"] = None

        # Convert video to full URL
        if instance.video:
            try:
                data["video"] = instance.video.url
            except Exception as e:
                print(f"Error occurred while fetching video URL: {e}")
                data["video"] = None

        return data

    def get_user_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None

    def get_is_viewed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.viewed_by.filter(id=request.user.id).exists()
        return False

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.liked_by.filter(id=request.user.id).exists()
        return False


class StoryViewerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "avatar"]


class StoryCommentSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = StoryComment
        fields = ["id", "story", "username", "avatar", "text", "created_at", "is_owner"]
        read_only_fields = ["user", "created_at"]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False

    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # 1. Capture the input (User might type "Newton" or "22-1234")
        login_input = attrs.get("username")

        if login_input:
            # 2. "Smart Search": Look for a user where Username OR Admission Number matches
            user = User.objects.filter(
                Q(username__iexact=login_input)  # Case-insensitive username
                | Q(admission_number__iexact=login_input)  # Case-insensitive admission no.
            ).first()

            if user:
                # 3. The Switch: If found, use the REAL username for authentication
                # This tricks the system into working even if they typed admission number
                attrs["username"] = user.username

        # 4. Standard Password Check (Let the parent class handle the heavy lifting)
        try:
            data = super().validate(attrs)
        except Exception:
            # If password is wrong, this generic error is safer
            raise AuthenticationFailed("Invalid credentials. Please check your password.")

        # 5. Add your custom response data
        data["id"] = self.user.id
        data["username"] = self.user.username
        data["email"] = self.user.email
        data["admission_number"] = self.user.admission_number
        data["points"] = self.user.points
        data["phone_number"] = getattr(self.user, "phone_number", "")

        if self.user.avatar:
            data["avatar"] = self.user.avatar.url

        return data


class UserSerializer(serializers.ModelSerializer):
    # 1. Custom Calculated Fields
    is_paid_member = serializers.SerializerMethodField()
    qr_code_data = serializers.SerializerMethodField()

    # 2. formatting the date
    membership_expiry = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "admission_number",
            "program",
            "avatar",
            "year_of_study",
            "phone_number",
            "is_paid_member",
            "membership_expiry",
            "points",  # Ensure points is here
            "attendance_percentage",
            "fcm_token",  # <--- Needed for Notifications
            "qr_code_data",  # <--- THIS WAS MISSING, CAUSING THE ERROR
        ]

    def get_qr_code_data(self, obj):
        # We return the admission number to be generated into a QR code
        return obj.admission_number

    def get_is_paid_member(self, obj):
        # Runs the logic in models.py (checking the date)
        return obj.is_active_member


class AppUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUpdate
        fields = ["id", "version_code", "version_name", "apk_file", "is_mandatory", "release_notes", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["user", "created_at"]


class ExamSerializer(serializers.ModelSerializer):
    day_name = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = "__all__"

    def get_day_name(self, obj):
        return obj.date.strftime("%A")

    def get_formatted_date(self, obj):
        return obj.date.strftime("%d %b %Y")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "password", "email", "admission_number", "phone_number", "program", "year_of_study"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
            admission_number=validated_data.get("admission_number", ""),
            phone_number=validated_data.get("phone_number", ""),
            program=validated_data.get("program", ""),
            year_of_study=validated_data.get("year_of_study", 1),
        )
        return user


class EventSerializer(serializers.ModelSerializer):
    # Add a field to check if the CURRENT user asking for events has RSVP'd
    has_rsvped = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["id", "title", "description", "date", "venue", "image", "has_rsvped"]

    def get_has_rsvped(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.rsvp_set.filter(user=request.user).exists()
        return False


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ["id", "title", "resource_type", "link", "file", "description"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class CommunityCommentSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = CommunityComment
        fields = ["id", "post", "username", "avatar", "text", "created_at", "is_owner"]
        read_only_fields = ["user", "created_at"]

    def get_is_owner(self, obj):
        user = self.context["request"].user
        return obj.user == user

    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class CommunityPostSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)
    likes = serializers.IntegerField(source="total_likes", read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        # 🟢 NEW: Add 'image' to the fields list
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
        user = self.context["request"].user
        if user.is_authenticated:
            return obj.liked_by.filter(id=user.id).exists()
        return False

    def get_is_owner(self, obj):
        user = self.context["request"].user
        return obj.user == user

    def get_username(self, obj):
        return "Anonymous Student" if obj.is_anonymous else obj.user.username

    def get_avatar(self, obj):
        if obj.is_anonymous:
            return None
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class LostItemSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.ImageField(source="user.avatar", read_only=True)

    class Meta:
        model = LostItem
        fields = "__all__"
        read_only_fields = ["user", "created_at", "is_resolved"]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user:
            return obj.user == request.user
        return False


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = "__all__"


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"


class AppConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppConfig
        fields = ["maintenance_mode", "maintenance_title", "maintenance_message"]


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = "__all__"


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.ReadOnlyField(source="achievement.name")
    achievement_description = serializers.ReadOnlyField(source="achievement.description")
    achievement_icon = serializers.ReadOnlyField(source="achievement.icon_url")

    class Meta:
        model = UserAchievement
        fields = ["id", "achievement_name", "achievement_description", "achievement_icon", "earned_at"]


class GroupMessageSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = GroupMessage
        fields = ["id", "username", "avatar", "content", "timestamp"]

    def get_avatar(self, obj):
        if obj.user.avatar:
            return obj.user.avatar.url
        return None


class StudyGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="members.count", read_only=True)
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = StudyGroup
        fields = ["id", "name", "course_code", "description", "member_count", "is_member", "created_at", "creator"]
        read_only_fields = ["creator"]

    def get_is_member(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return obj.members.filter(id=user.id).exists()
        return False
