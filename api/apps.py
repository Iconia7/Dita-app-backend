from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
import os
from django.conf import settings

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # 1. Initialize Firebase (Your existing logic)
        if not firebase_admin._apps:
            try:
                cred_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', None)
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    print(f"✅ Firebase initialized successfully in apps.py")
                else:
                    print(f"❌ ERROR: serviceAccountKey.json NOT FOUND at: {cred_path}")
            except Exception as e:
                print(f"❌ Firebase Initialization Failed: {e}")

        # 2. IMPORT SIGNALS (THIS IS CRITICAL)
        # Without this line, your signals.py file is ignored!
        import api.signals