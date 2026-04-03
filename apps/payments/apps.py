from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """Configuration for the Payments app, which includes models and views for handling payment processing and callbacks."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    label = "payments"
