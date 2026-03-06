from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from firebase_admin import messaging
from api.models import User


class Command(BaseCommand):
    help = "Sends push notifications to members whose subscription expires in 7 days"

    def handle(self, *args, **kwargs):
        # 1. Calculate the target date (Today + 7 days)
        today = timezone.now().date()
        target_date = today + timedelta(days=7)

        self.stdout.write(f"🔍 Checking for memberships expiring on: {target_date}")

        # 2. Find Users
        # We filter where the expiry DATE matches our target date
        expiring_users = User.objects.filter(membership_expiry__date=target_date, fcm_token__isnull=False).exclude(
            fcm_token=""
        )

        count = expiring_users.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("No memberships expiring in 7 days."))
            return

        self.stdout.write(f"📢 Found {count} users. Sending notifications...")

        # 3. Send Notifications
        success_count = 0
        for user in expiring_users:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="Membership Expiring Soon ⏳",
                        body=f"Hi {user.username}, your DITA membership expires in 7 days. Renew now to keep access!",
                    ),
                    token=user.fcm_token,
                    data={"click_action": "FLUTTER_NOTIFICATION_CLICK", "type": "reminder"},
                )
                messaging.send(message)
                success_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send to {user.username}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully sent {success_count} reminders."))
