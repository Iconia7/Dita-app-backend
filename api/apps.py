from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
import os
from django.conf import settings

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Only initialize if not already initialized
        if not firebase_admin._apps:
            try:
                # Get path from settings
                cred_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', None)
                
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    print(f"✅ Firebase initialized successfully in apps.py")
                else:
                    print(f"❌ ERROR: serviceAccountKey.json NOT FOUND at: {cred_path}")
                    
                    # DEBUGGING: List files in the secrets directory to check for typos
                    if os.environ.get('RENDER'):
                        secret_dir = '/etc/secrets/'
                        if os.path.exists(secret_dir):
                            print(f"📂 Contents of {secret_dir}: {os.listdir(secret_dir)}")
                        else:
                            print(f"❌ Directory {secret_dir} does not exist!")

            except Exception as e:
                print(f"❌ Firebase Initialization Failed: {e}")