from django.db.models.signals import post_save
from django.dispatch import receiver
from firebase_admin import messaging
from .models import Announcement, User

@receiver(post_save, sender=Announcement)
def send_push_notification(sender, instance, created, **kwargs):
    # Only send for NEW announcements that are marked ACTIVE
    if created and instance.is_active: 
        print(f"📢 New Announcement: {instance.title}. Preparing notification...")

        # 1. Get all tokens
        tokens = list(User.objects.exclude(fcm_token__isnull=True).exclude(fcm_token__exact='').values_list('fcm_token', flat=True))
        
        if not tokens:
            print("⚠️ No devices registered for notifications.")
            return

        # --- UPDATE START ---

        # 2. Construct the Message
        message = messaging.MulticastMessage(
            data={
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "title": instance.title,         # Send full title in data
                "message_body": instance.message, # Send FULL message in data (not truncated)
                "type": "announcement"
            },
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority='high', # Forces wake-up in background
                ttl=0,           # 0 = Deliver immediately or drop (prevents stale alerts)
            )
        )
        # --- UPDATE END ---

        # 3. Send (Using the Modern Method)
        try:
            # We try the new method first
            if hasattr(messaging, 'send_each_for_multicast'):
                response = messaging.send_each_for_multicast(message)
                print(f"✅ Notification sent! Success: {response.success_count}")
            
            # Fallback for older versions if upgrade didn't work
            elif hasattr(messaging, 'send_multicast'):
                response = messaging.send_multicast(message)
                print(f"✅ Notification sent! Success: {response.success_count}")
            
            else:
                print("❌ Error: Firebase library version incompatible. Please upgrade firebase-admin.")

        except Exception as e:
            print(f"❌ Error sending notification: {e}")