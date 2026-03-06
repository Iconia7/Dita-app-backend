from .base import *

DEBUG = True

ALLOWED_HOSTS += ['*']

# SQLite by default, Postgres if DATABASE_URL is set
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=0,
        ssl_require=False
    )

# Use local file storage in development
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Google credentials
GOOGLE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'config', 'serviceAccountKey.json')