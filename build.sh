#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Upgrade pip first (Fixes many version errors)
pip install --upgrade pip

# 2. Install your requirements
pip install -r requirements.txt

# 3. Django setup
python manage.py collectstatic --no-input
python manage.py migrate