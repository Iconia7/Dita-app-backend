import os

from django.db.models.signals import post_save
from django.dispatch import receiver
from firebase_admin import messaging

from .models import Achievement, Announcement, User, UserAchievement


@receiver(post_save, sender=Announcement)
def send_push_notification(sender, instance, created, **kwargs):
    # Only send for NEW announcements that are marked ACTIVE
    if created and instance.is_active:
        print(f"📢 New Announcement: {instance.title}. Preparing notification...")
        image_url = ""
        if instance.image:
            # Check if it's already a full Cloudinary URL
            if instance.image.url.startswith("http"):
                image_url = instance.image.url
            else:
                # If it's a relative path (local storage), prepend domain from env
                base_url = os.environ.get("BACKEND_URL", "https://api.dita.co.ke")
                image_url = f"{base_url}{instance.image.url}"

        # 1. Get all tokens
        tokens = list(
            User.objects.exclude(fcm_token__isnull=True)
            .exclude(fcm_token__exact="")
            .values_list("fcm_token", flat=True)
        )

        if not tokens:
            print("⚠️ No devices registered for notifications.")
            return

        # --- UPDATE START ---

        # 2. Construct the Message
        message = messaging.MulticastMessage(
            data={
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "title": instance.title,  # Send full title in data
                "message_body": instance.message,  # Send FULL message in data (not truncated)
                "type": "announcement",
                "image": image_url,
            },
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",  # Forces wake-up in background
                ttl=0,  # 0 = Deliver immediately or drop (prevents stale alerts)
            ),
        )
        # --- UPDATE END ---

        # 3. Send (Using the Modern Method)
        try:
            # We try the new method first
            if hasattr(messaging, "send_each_for_multicast"):
                response = messaging.send_each_for_multicast(message)
                print(f"✅ Notification sent! Success: {response.success_count}")

            # Fallback for older versions if upgrade didn't work
            elif hasattr(messaging, "send_multicast"):
                response = messaging.send_multicast(message)
                print(f"✅ Notification sent! Success: {response.success_count}")

            else:
                print("❌ Error: Firebase library version incompatible. Please upgrade firebase-admin.")

        except Exception as e:
            print(f"❌ Error sending notification: {e}")


@receiver(post_save, sender=User)
def check_user_achievements(sender, instance, **kwargs):
    """
    Automatically grants achievements based on points and game stats.
    """

    def grant_achievement(name, description, threshold):
        """Helper to grant achievement if not already earned"""
        achievement, _ = Achievement.objects.get_or_create(
            name=name, defaults={"description": description, "points_threshold": threshold}
        )
        UserAchievement.objects.get_or_create(user=instance, achievement=achievement)

    # Point-based achievements
    if instance.points >= 1000:
        grant_achievement("Point Collector", "Earned 1000 total points!", 1000)

    if instance.points >= 500:
        grant_achievement("Scholar", "Reached 500 points in academic activities!", 500)

    if instance.points >= 200:
        grant_achievement("Event Explorer", "Attended multiple events and earned 200+ points!", 200)

    # Binary Tac-Toe achievements
    if instance.binary_wins_hard >= 5:
        grant_achievement("AI Slayer", "Defeated the hard AI 5 times!", 0)

    if instance.binary_wins_easy + instance.binary_wins_medium + instance.binary_wins_hard >= 10:
        grant_achievement("Strategy Master", "Won 10 Binary Tac-Toe games!", 0)

    # Snake achievements
    if instance.snake_high_score >= 1000:
        grant_achievement("Speed Demon", "Scored 1000+ points in Snake!", 0)

    # General gaming achievements
    games_played = (
        (instance.snake_games_played > 0) + (instance.binary_games_played > 0) + (instance.ram_games_played > 0)
    )
    if games_played >= 3:
        grant_achievement("Game Hobbyist", "Played all 3 games!", 0)


@receiver(post_save, sender=UserAchievement)
def notify_achievement_unlock(sender, instance, created, **kwargs):
    """
    Send push notification when new achievement is unlocked.
    """
    if not created:
        return  # Only notify for NEW achievements

    user = instance.user
    achievement = instance.achievement

    # Only send if user has an FCM token
    if not user.fcm_token:
        return

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="🏆 Achievement Unlocked!",
                body=f"{achievement.name}: {achievement.description}",
            ),
            token=user.fcm_token,
            data={
                "type": "achievement",
                "achievement_id": str(achievement.id),
                "achievement_name": achievement.name,
            },
        )

        messaging.send(message)
        print(f"✅ Achievement notification sent to {user.username}: {achievement.name}")

    except Exception as e:
        print(f"❌ Failed to send achievement notification to {user.username}: {e}")
