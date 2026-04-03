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

## API Documentation

Interactive API docs are available via Swagger UI once the server is running.

| URL                                 | Description                                |
| ----------------------------------- | ------------------------------------------ |
| `http://localhost:8000/api/docs/`   | Swagger UI — browse and test all endpoints |
| `http://localhost:8000/api/redoc/`  | ReDoc — clean readable API reference       |
| `http://localhost:8000/api/schema/` | Raw OpenAPI schema (JSON)                  |

Swagger UI lets you authenticate with a JWT token and test endpoints directly from the browser without needing Postman.

---

## Firebase Setup

Place your `serviceAccountKey.json` in:

```
config/serviceAccountKey.json
```

On Render (production), upload it as a Secret File at `/etc/secrets/serviceAccountKey.json`.

---

## Code Quality

### Formatting and Linting

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 .
```

### Running all checks with tox

```bash
tox
```

Tox runs flake8 in an isolated environment. Configuration is in `tox.ini`. To see verbose output:

```bash
tox -v
```

### Config files

| Tool   | Config location                       |
| ------ | ------------------------------------- |
| black  | `pyproject.toml` under `[tool.black]` |
| isort  | `pyproject.toml` under `[tool.isort]` |
| flake8 | `.flake8`                             |
| tox    | `tox.ini`                             |

---

## Settings

Settings are split by environment under `config/settings/`:

| File             | Used when                      |
| ---------------- | ------------------------------ |
| `base.py`        | Shared across all environments |
| `development.py` | Local development (default)    |
| `production.py`  | Render deployment              |

To switch environments, set the `DJANGO_SETTINGS_MODULE` env var:

```bash
# development (default via manage.py)
DJANGO_SETTINGS_MODULE=config.settings.development

# production
DJANGO_SETTINGS_MODULE=config.settings.production
```

Key differences between environments:

- **Development** — uses local file storage for media, SQLite by default, SSL off
- **Production** — uses Cloudinary for media, SSL enforced, full security headers enabled

---

## Requirements

Dependencies are split by environment under `requirements/`:

```bash
pip install -r requirements/local.txt   # development
pip install -r requirements/prod.txt    # production
pip install -r requirements/testing.txt # testing
```

---

## Deployment

Set the following environment variables on the deployment platform (e.g. Render):

```
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=
DATABASE_URL=
REDIS_URL=
```

Upload `serviceAccountKey.json` as a Secret File at path `/etc/secrets/serviceAccountKey.json`.

---

## Management Commands

```bash
# Send membership expiry reminders
python manage.py send_reminders
```
