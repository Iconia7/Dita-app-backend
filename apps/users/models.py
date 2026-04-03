from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser."""

    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    points = models.IntegerField(default=0)
    snake_high_score = models.IntegerField(default=0)
    snake_games_played = models.IntegerField(default=0)
    binary_wins_easy = models.IntegerField(default=0)
    binary_wins_medium = models.IntegerField(default=0)
    binary_wins_hard = models.IntegerField(default=0)
    binary_games_played = models.IntegerField(default=0)
    ram_levels_completed = models.IntegerField(default=0)
    ram_games_played = models.IntegerField(default=0)
    admission_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    program = models.CharField(max_length=100, null=True, blank=True)
    year_of_study = models.IntegerField(default=1)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    membership_expiry = models.DateTimeField(null=True, blank=True)

    @property
    def attendance_percentage(self):
        """Calculate the attendance percentage based on attended events and total events."""
        from apps.events.models import Event

        total_events = Event.objects.count()

        if total_events == 0:
            return 0

        # 'attended_events' is the related_name we set in the Event model
        attended_count = self.attended_events.count()

        # Calculate Percentage
        return int((attended_count / total_events) * 100)

    @property
    def is_active_member(self):
        """Check if the user's membership is still active based on the expiry date."""
        if self.membership_expiry and self.membership_expiry > timezone.now():
            return True
        return False


class Achievement(models.Model):
    """Model representing an achievement that users can earn."""

    name = models.CharField(max_length=100)
    description = models.TextField()
    icon_url = models.URLField(blank=True, null=True)
    points_threshold = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    """Model representing the achievements earned by users."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ensure that a user can earn a specific achievement only once."""

        unique_together = ("user", "achievement")

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
