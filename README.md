# Dita App Backend

Django REST API backend for the DITA mobile app — a platform for university CS students featuring events, academics, community, payments, and real-time chat.

---

## Tech Stack

- **Django 4.2** + Django REST Framework
- **PostgreSQL** — production database
- **Redis** — WebSocket channel layer
- **Django Channels** + Daphne — WebSocket/ASGI server
- **Firebase Admin SDK** — phone authentication & push notifications
- **Cloudinary** — media storage (production)
- **PayHero** — M-Pesa STK push payments
- **JWT** — authentication via `djangorestframework-simplejwt`

---

## Getting Started

### Prerequisites

- Python 3.13+
- Docker (for PostgreSQL and Redis)

### 1. Clone the repo

```bash
git clone https://github.com/your-org/Dita-app-backend.git
cd Dita-app-backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements/local.txt
```

### 4. Set up environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Some of the required variables:

```env
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgres://myuser:mypassword@localhost:5432/dita_db?sslmode=disable
REDIS_URL=redis://localhost:6379

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

PAYHERO_CALLBACK_SECRET=
AUTH_HEADER=
CHANNEL_ID=
BACKEND_URL=https://api.dita.co.ke
```

### 5. Start PostgreSQL and Redis with Docker

```bash
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=dita_db \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  postgres:alpine

docker run -d -p 6379:6379 redis:alpine
```

### 6. Run migrations

```bash
python manage.py migrate
```

### 7. Create a superuser

```bash
python manage.py createsuperuser
```

### 8. Run the development server

```bash
python manage.py runserver
```

---

## Firebase Setup

Docs coming soon

---

## Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 .

# Run all checks via tox
tox
```

---

## Deployment

Docs coming soon

## Management Commands

```bash
# Send membership expiry reminders
python manage.py send_reminders
```
