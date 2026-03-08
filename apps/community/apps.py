from django.apps import AppConfig


class CommunityConfig(AppConfig):
    """Configuration for the Community app, which includes models and views for community posts, comments, lost items, and stories."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.community"
    label = "community"
