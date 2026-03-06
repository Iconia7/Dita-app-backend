from django.contrib.auth.admin import UserAdmin

from .models import Achievement, User, UserAchievement
from django.contrib import admin


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin interface for the User model, displaying additional fields and allowing filtering by membership status and program."""

    list_display = (
        "username",
        "admission_number",
        "program",
        "is_active_member",
        "membership_expiry",
        "points",
        "fcm_token",
    )
    list_filter = ("membership_expiry", "program", "year_of_study", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Student Details",
            {
                "fields": (
                    "admission_number",
                    "program",
                    "year_of_study",
                    "phone_number",
                    "membership_expiry",
                    "points",
                    "fcm_token",
                )
            },
        ),
    )


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    """Custom admin interface for the Achievement model."""

    list_display = ("name", "points_threshold")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    """Custom admin interface for the UserAchievement model."""

    list_display = ("user", "achievement", "earned_at")
