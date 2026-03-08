from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    """Configuration for the Academics app, which includes models for exams and tasks."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.academics"
    label = "academics"
