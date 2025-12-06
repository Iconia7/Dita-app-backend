#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# --- ADD THIS LINE BELOW ---
# This tries to create the user using the Env Vars you set in Step 1.
# The '|| true' part ensures the build doesn't fail if the user already exists.
python manage.py createsuperuser --noinput || true