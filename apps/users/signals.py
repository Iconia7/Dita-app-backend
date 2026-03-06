from django.db.models.signals import post_save
from django.dispatch import receiver
from firebase_admin import messaging

from .models import Achievement, User, UserAchievement


@receiver(post_save, sender=User)
def check_user_achievements(sender, instance, **kwargs):
    """
    Signal receiver that checks for user achievements whenever a User instance is saved,
    and grants achievements based on the user's points and game statistics.
    """

    def grant_achievement(name, description, threshold):
        """Helper function to grant an achievement to the user if they meet the criteria."""
        achievement, _ = Achievement.objects.get_or_create(
            name=name, defaults={"description": description, "points_threshold": threshold}
        )
        UserAchievement.objects.get_or_create(user=instance, achievement=achievement)

    # Check for various achievements based on the user's points and game stats
    if instance.points >= 1000:
        grant_achievement("Point Collector", "Earned 1000 total points!", 1000)
    if instance.points >= 500:
        grant_achievement("Scholar", "Reached 500 points in academic activities!", 500)
    if instance.points >= 200:
        grant_achievement("Event Explorer", "Attended multiple events and earned 200+ points!", 200)
    if instance.binary_wins_hard >= 5:
        grant_achievement("AI Slayer", "Defeated the hard AI 5 times!", 0)
    if instance.binary_wins_easy + instance.binary_wins_medium + instance.binary_wins_hard >= 10:
        grant_achievement("Strategy Master", "Won 10 Binary Tac-Toe games!", 0)
    if instance.snake_high_score >= 1000:
        grant_achievement("Speed Demon", "Scored 1000+ points in Snake!", 0)
    games_played = (
        (instance.snake_games_played > 0) + (instance.binary_games_played > 0) + (instance.ram_games_played > 0)
    )
    if games_played >= 3:
        grant_achievement("Game Hobbyist", "Played all 3 games!", 0)


@receiver(post_save, sender=UserAchievement)
def notify_achievement_unlock(sender, instance, created, **kwargs):
    """Signal receiver that sends a notification to the user when they unlock a new achievement, using Firebase Cloud Messaging."""
    if not created:
        return
    user = instance.user
    achievement = instance.achievement
    if not user.fcm_token:
        return
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="🏆 Achievement Unlocked!",
                body=f"{achievement.name}: {achievement.description}",
            ),
            token=user.fcm_token,
            data={"type": "achievement", "achievement_id": str(achievement.id), "achievement_name": achievement.name},
        )
        messaging.send(message)
        print(f"✅ Achievement notification sent to {user.username}: {achievement.name}")
    except Exception as e:
        print(f"❌ Failed to send achievement notification to {user.username}: {e}")
