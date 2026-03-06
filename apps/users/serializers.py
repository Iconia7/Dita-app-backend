from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Achievement, User, UserAchievement


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer for obtaining JWT tokens, allowing login with either username or admission number."""

    def validate(self, attrs):
        """Override the validate method to allow login with either username or admission number."""
        login_input = attrs.get("username")

        # If the input is not a username, try to find a user with the given admission number
        # and set the username for authentication purposes
        if login_input:
            user = User.objects.filter(
                Q(username__iexact=login_input) | Q(admission_number__iexact=login_input)
            ).first()
            if user:
                attrs["username"] = user.username
        try:
            data = super().validate(attrs)
        except Exception:
            raise AuthenticationFailed("Invalid credentials. Please check your password.")

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
    """Serializer for the User model, including additional fields for membership status and QR code data."""

    is_paid_member = serializers.SerializerMethodField()
    qr_code_data = serializers.SerializerMethodField()
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
            "points",
            "attendance_percentage",
            "fcm_token",
            "qr_code_data",
        ]

    def get_qr_code_data(self, obj):
        """Generate QR code data based on the user's admission number."""
        return obj.admission_number

    def get_is_paid_member(self, obj):
        """Determine if the user is a paid member based on their membership expiry date."""
        return obj.is_active_member


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration, allowing creation of new users with necessary fields."""

    password = serializers.CharField(write_only=True)

    class Meta:
        """Meta class specifying the model and fields for the registration serializer."""

        model = User
        fields = ["username", "password", "email", "admission_number", "phone_number", "program", "year_of_study"]

    def create(self, validated_data):
        """Override the create method to create a new user with the provided validated data."""
        return User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
            admission_number=validated_data.get("admission_number", ""),
            phone_number=validated_data.get("phone_number", ""),
            program=validated_data.get("program", ""),
            year_of_study=validated_data.get("year_of_study", 1),
        )


class AchievementSerializer(serializers.ModelSerializer):
    """Serializer for the Achievement model, allowing serialization of achievement data."""

    class Meta:
        """Meta class specifying the model and fields for the achievement serializer."""

        model = Achievement
        fields = "__all__"


class UserAchievementSerializer(serializers.ModelSerializer):
    """Serializer for the UserAchievement model, including related achievement details."""

    achievement_name = serializers.ReadOnlyField(source="achievement.name")
    achievement_description = serializers.ReadOnlyField(source="achievement.description")
    achievement_icon = serializers.ReadOnlyField(source="achievement.icon_url")

    class Meta:
        """Meta class specifying the model and fields for the user achievement serializer."""

        model = UserAchievement
        fields = ["id", "achievement_name", "achievement_description", "achievement_icon", "earned_at"]
