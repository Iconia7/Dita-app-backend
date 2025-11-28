import os
from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # 1. Register Signals (Trigger logic)
        import api.signals 

        # 2. Initialize Firebase (only if not already initialized)
        if not firebase_admin._apps:
            # Construct path to the JSON file
            # Assuming file is in dita_backend/dita_backend/serviceAccountKey.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(base_dir, 'dita_backend', 'serviceAccountKey.json')
            
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin Initialized Successfully")
            except Exception as e:
                print(f"❌ Firebase Init Error: {e}")