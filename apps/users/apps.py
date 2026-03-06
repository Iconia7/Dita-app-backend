import os
import firebase_admin
from django.apps import AppConfig
from django.conf import settings
from firebase_admin import credentials


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"

    def ready(self):
        if not firebase_admin._apps:
            try:
                cred_path = getattr(settings, "GOOGLE_CREDENTIALS_PATH", None)
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase initialized successfully")
                else:
                    print(f"❌ ERROR: serviceAccountKey.json NOT FOUND at: {cred_path}")
            except Exception as e:
                print(f"❌ Firebase Initialization Failed: {e}")

        import apps.users.signals  # noqa: F401
