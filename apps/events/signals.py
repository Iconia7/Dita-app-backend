import os

from django.db.models.signals import post_save
from django.dispatch import receiver

from firebase_admin import messaging

from apps.users.models import User

from .models import Announcement


@receiver(post_save, sender=Announcement)
def send_push_notification(sender, instance, created, **kwargs):
    """Signal receiver that sends a push notification to all users when a new announcement is created, using Firebase Cloud Messaging."""
    if created and instance.is_active:
        print(f"📢 New Announcement: {instance.title}. Preparing notification...")
        image_url = ""
        if instance.image:
            if instance.image.url.startswith("http"):
                image_url = instance.image.url
            else:
                base_url = os.environ.get("BACKEND_URL", "https://api.dita.co.ke")
                image_url = f"{base_url}{instance.image.url}"

        tokens = list(
            User.objects.exclude(fcm_token__isnull=True)
            .exclude(fcm_token__exact="")
            .values_list("fcm_token", flat=True)
        )

        if not tokens:
            print("⚠️ No devices registered for notifications.")
            return

        message = messaging.MulticastMessage(
            data={
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "title": instance.title,
                "message_body": instance.message,
                "type": "announcement",
                "image": image_url,
            },
            tokens=tokens,
            android=messaging.AndroidConfig(priority="high", ttl=0),
        )

        # Attempt to send the notification and handle potential errors gracefully, with logging for success and failure cases.
        try:
            if hasattr(messaging, "send_each_for_multicast"):
                response = messaging.send_each_for_multicast(message)
                print(f"✅ Notification sent! Success: {response.success_count}")
            elif hasattr(messaging, "send_multicast"):
                response = messaging.send_multicast(message)
                print(f"✅ Notification sent! Success: {response.success_count}")
            else:
                print("❌ Error: Firebase library version incompatible.")
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
