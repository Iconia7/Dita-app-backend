from django.apps import AppConfig


class EventsConfig(AppConfig):
    """
    Configuration for the Events app, which includes models for events, announcements, and RSVPs.
    This configuration sets up the default auto field type, app name, and label, and imports signal handlers when the app is ready.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
    label = "events"

    def ready(self):
        """Import signal handlers for the Events app to ensure they are registered when the app is ready."""
        import apps.events.signals  # noqa: F401
